
from flask import Flask, render_template, redirect, url_for, request, jsonify
from flask_socketio import SocketIO
from nlp_engine import nlp_engine
import boto3
from utils import df_to_text
import os
from io import StringIO
import io
from PIL import Image
from config import vital_sign_var_to_text
from utils import *
import time
import pandas as pd 
from dotenv import load_dotenv

# Load environment variables from .env
#load_dotenv()

# Access your API key
s3_key_id = os.getenv("S3_KEY_ID")
s3_secret_key = os.getenv("S3_SECRET_KEY")

app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet')
agent = nlp_engine()
received_data = None
temp_img_path = './static/local_data/show_data/temp.jpg'


bucket_name = 'remoni'
s3_client = boto3.client( 
    service_name='s3',
    region_name='us-east-1',
    aws_access_key_id=s3_key_id,
    aws_secret_access_key=s3_secret_key
)


print('Starting the server')
@app.route('/')
def index_get():
    #return 'Hi'
    return render_template('doctor.html')

@app.route("/fall_signal", methods=['POST'])
def fall_signal():
    # Emit a message to all connected clients
    noti = request.get_json().get("anomaly")
    socketio.emit('fall_alert', {'message': noti})
    return jsonify({'status': 'success'})

def get_raw_data_from_s3(key):
    #key = '00001/time_series/11.csv' # this is the path to save data inside the above bucket
    # get data from AWS S3
    print('=========KEY S3==========')
    print(key)
    
    obj = s3_client.get_object(Bucket=bucket_name, Key=key)
    data = obj['Body'].read()
    #print(data)
    return data

def get_data_from_s3(key, type_of_data:str):
    # download data
    try:
        #raw_data = get_raw_data_from_s3(key)
        obj = s3_client.get_object(Bucket=bucket_name, Key=key)
        raw_data = obj['Body'].read()
        print('getting raw data')
        # process the raw data based on type_of_data
        if type_of_data == 'vital_sign':
            data_decoded = raw_data.decode('utf-8')
            df = pd.read_csv(StringIO(data_decoded))
            return df

        elif type_of_data == 'image':
            from PIL import Image
            import io
            data_decoded = io.BytesIO(raw_data)
            # Open the image using Pillow and convert it to RGB
            image = Image.open(data_decoded).convert('RGB') # PIL Image object
            image_path = get_serial_path('./static/local_data/show_data/')
            image.save(image_path)
            return image_path
    except: return None
    """
    # process the raw data based on type_of_data
    if type_of_data == 'vital_sign':
        data_decoded = raw_data.decode('utf-8')
        df = pd.read_csv(StringIO(data_decoded))
        return df

    elif type_of_data == 'image':
        from PIL import Image
        import io
        data_decoded = io.BytesIO(raw_data)
        # Open the image using Pillow and convert it to RGB
        image = Image.open(data_decoded).convert('RGB') # PIL Image object
        image_path = get_serial_path('./static/local_data/show_data/')
        image.save(image_path)
        return image_path
    """
def get_data_from_edge(type_of_data: str):
    # Send a signal to the local server via S3 to request real-time data
    s3_client.put_object(Body=type_of_data, Bucket=bucket_name, Key='signal_file.txt')
    
    # Waiting for edge device to update data to S3
    if type_of_data == 'vital_sign':
        received_key = 'real_time_data.csv'
    elif type_of_data == 'image':
        received_key = 'instant.jpg'
    
    i = 0
    while True:
        #try:
        print('connecting to s3')
        instant_data = get_data_from_s3(received_key, type_of_data)
        print(instant_data)
        if isinstance(instant_data, pd.DataFrame): break
        elif isinstance(instant_data, str): break
        time.sleep(3)    
        #except:
        #    time.sleep(1)
        #    i+=1
        #    print(i)
        #    if i==60: break


    try:
        # Delete the file from the S3 bucket
        s3_client.delete_object(Bucket='remoni', Key=received_key)
        print(f"File '{received_key}' deleted successfully")
    except Exception as e:
        print(f"Error deleting file '{received_key}': {str(e)}")
    
    return instant_data


@app.route("/chat", methods=['POST'])
def chat():
    # receive question from user 
    question = request.get_json().get("message")
    
    # chat API
    agent.intent_detection(question) # update the intent_dict
    #agent.intent_dict['patient_id'] = '00001'
    agent.patient_id = '00001'
    agent.check_and_update_patient_id() # check and update patient id #TODO: integrate this function into front-end
    agent.show_data_list=[]
    
    ################################
    ########## VITAL SIGN ##########
    ################################

    if len(agent.intent_dict['vital_sign'])>0:
        ########## get real-time data from the EDGE DEVICE ##########
        if (len(agent.intent_dict['list_date']) == 0) and (len(agent.intent_dict['list_time']) == 0):
            # get raw dataframe
            vital_sign_raw_df = get_data_from_edge('vital_sign')
            # process raw dataframe
            vital_sign_filtered_df = filter_raw_df(vital_sign_raw_df, agent.intent_dict, is_current=True)
            vital_signs_text = df_to_text(vital_sign_filtered_df, agent.intent_dict)
            agent.vital_signs_text = vital_signs_text

        ########## get historical data from the AWS S3 ##########
        else:
            agent.process_special_historical_data_retrieval() # sometime the question is not giving the whole context, this one is used to fill the missing context
            
            year_month_list = extract_unique_year_month(agent.intent_dict['list_date'])
            vital_sign_raw_df = pd.DataFrame() # Initialize an empty DataFrame
            # get raw dataframe
            for year_month in year_month_list:
                s3_csv_path = f"{agent.patient_id}/time_series/{year_month}.csv"
                temp_df = get_data_from_s3(s3_csv_path, 'vital_sign')
                vital_sign_raw_df = pd.concat([vital_sign_raw_df, temp_df], ignore_index=True)
            
            # process raw dataframe
            vital_sign_filtered_df = filter_raw_df(vital_sign_raw_df, agent.intent_dict, is_current=False)
            vital_signs_text = df_to_text(vital_sign_filtered_df, agent.intent_dict)
            agent.vital_signs_text = vital_signs_text
            
            ########## PLOT ##########
            if agent.intent_dict['is_plot']:
                for item in agent.intent_dict['vital_sign']:
                    figure_path =plot_vital_sign(vital_sign_filtered_df, item)
                    agent.show_data_list.append(figure_path)
    
    ################################
    ##########   IMAGES   ##########
    ################################

    if agent.intent_dict['recognition'] or agent.intent_dict['is_image']: # check if we need to get the vital sign
        ########## get real-time image from the EDGE DEVICE ##########
        image_path_list = []
        if (len(agent.intent_dict['list_date']) == 0) and (len(agent.intent_dict['list_time']) == 0): 
            image_path = get_data_from_edge('image') # already save data to temp_img_path
            image_path_list.append(image_path)
            
        ########## get historical data from the AWS S3 ##########
        else: 
            agent.process_special_historical_data_retrieval() 
            # prepare key to retrieve data from s3
            timestamp_list = combine_data_and_time(agent.intent_dict['list_date'], agent.intent_dict['list_time'])
            grouped_timestamp = process_key_to_retrieve_image(timestamp_list)
            # get image from s3
            for s3_image_folder in list(grouped_timestamp.keys()):
                for s3_image_file in grouped_timestamp[s3_image_folder]:
                    s3_image_path = f"{agent.patient_id}/image/{s3_image_folder}/{s3_image_file}.jpg"
                    image_path = get_data_from_s3(s3_image_path, 'image')
                    image_path_list.append(image_path)
                    
        
        # check if the question asks for showing images
        if agent.intent_dict['is_image']:
            agent.show_data_list = image_path_list
            print(agent.show_data_list)
        ########## RECOGNITION ##########
        if agent.intent_dict['recognition']:
            agent.vision_llm(image_path_list)
        
    ################################
    #########   ENDPOINT   #########
    ################################
    
    patient_info = agent.patient_meta_df[agent.patient_meta_df['patient_id']==int(agent.patient_id)]
    output = agent.endpoint_llm(patient_info, question)
        
    # post processing output
    output = output.split('\n\n')
    output = "<br><br>".join(output)
    output = output.split('\n')
    output = "<br>".join(output)
    #print(output)
    message = {"answer": output}
    if agent.show_data_list:
        message["show_list"]= agent.show_data_list
    
    #with open('database/conv.json', 'w') as conv:
    #    json.dump(conv, conv)
    return (message)
'''
@app.route("/chat", methods=['POST'])
def chat():
    # receive question from user 
    question = request.get_json().get("message")
    message = {"answer": "OK OK OK !"}
    message["show_list"] = ['/static/local_data/12_00_00.jpg', '/static/local_data/12_00_30.jpg','/static/images/patient-3.png']
    return (message)
'''

if __name__ == '__main__':
    #app.run(host='0.0.0.0', port=8080)
    socketio.run(app, host='0.0.0.0', port=8080)
