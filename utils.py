import re
from config import vital_sign_var_to_text
import matplotlib
matplotlib.use('Agg')  # Set the backend to Agg
import matplotlib.pyplot as plt
from collections import defaultdict
import os

def combine_data_and_time(list_date, list_time):
    # combine date and time
    time_stamp_list = []
    for date in list_date:
        for time in list_time:
            time_stamp = f'{date} {time}'
            time_stamp_list.append(time_stamp)
            
    return time_stamp_list

def get_serial_path(data_folder_path):
    # Get a list of all files in the folder
    files = os.listdir(data_folder_path)

    # Filter out files that follow the pattern XX.jpg where XX is a number
    image_files = [f for f in files if f.endswith('.jpg') and f[:-4].isdigit()]

    # Extract the indices and find the maximum index
    indices = [int(f.split('.')[0]) for f in image_files]
    max_index = max(indices) if indices else 0

    # Determine the filename for the new image
    new_index = max_index + 1
    new_filename = f"{new_index:02d}.jpg"
    new_filepath = os.path.join(data_folder_path, new_filename)
    return new_filepath


def get_serial_path_plot(data_folder_path):
    # Get a list of all files in the folder
    files = os.listdir(data_folder_path)

    # Filter out files that follow the pattern XX.jpg where XX is a number
    image_files = [f for f in files if f.endswith('.png') and f[:-4].isdigit()]

    # Extract the indices and find the maximum index
    indices = [int(f.split('.')[0]) for f in image_files]
    max_index = max(indices) if indices else 0

    # Determine the filename for the new image
    new_index = max_index + 1
    new_filename = f"{new_index:02d}.png"
    new_filepath = os.path.join(data_folder_path, new_filename)
    return new_filepath

# extract patient_id from a text by find words matching the format of the id 
def extract_patient_id_from_text(text):
    # Regular expression pattern to match an ID like '00001'
    pattern = r"\d{5}"

    # Search for the pattern in the user response
    match = re.search(pattern, text)

    # Extract the ID if a match is found
    if match:
        patient_id = match.group(0)
        return patient_id
    
    else:
        return 'unknown'



# transform a dataframe into text with necessary columns
def filter_raw_df(df, intent_dict, is_current):
    if not is_current: # user is not asking for current data
        # combine date and time
        time_stamp_list = combine_data_and_time(intent_dict['list_date'], intent_dict['list_time'])
   
    else: 
        time_stamp_list = [df['time_stamp'][0]] # if user ask for current data, df just has one row
    
    # filter the df columns
    columns = ['time_stamp'] + intent_dict['vital_sign'] # list of columns to filter out
    filtered_df = df[columns]
    
    # get rows with time_stamp in time_stamp_list
    filtered_df = filtered_df[filtered_df['time_stamp'].isin(time_stamp_list)].reset_index()
    return filtered_df
    

def df_to_text(df, intent_dict):   
    # convert the df into text to put into the endpoint prompt
    text = ''
    title_row = 'Timestamp (Year-Month-Day Hour:Minute:Second)'

    # 1. create the title row
    for vital_sign in intent_dict['vital_sign']:
        title_row += f', {vital_sign_var_to_text[vital_sign]}'
    
    text += f'{title_row} \n'  
    
    # 1. add data row into data_text
    for i in range(len(df)):
        row_text = df.iloc[i]['time_stamp']

        for vital_sign in intent_dict['vital_sign']:
            row_text += f', {df.iloc[i][vital_sign]}'
        
        text += f'{row_text} \n'
            
    return text


def plot_vital_sign(df, vital_sign):
    # sample data points to make sure the plot is clear
    if df.shape[0] <= 20:
        df_sampled = df
    else:
        sample_rate = len(df) // 20
        df_sampled = df.iloc[::sample_rate].copy()
    figure=plt.figure(figsize=(7,5))
    x=df_sampled.time_stamp
    y=df_sampled[vital_sign]
    plt.plot(x,y)
    plt.xticks(rotation=90)
    #save_path = f'./static/local_data/plot_{vital_sign}.png'
    save_path = get_serial_path_plot('./static/local_data/')
    figure.savefig(save_path, bbox_inches='tight')
    return save_path

def extract_unique_year_month(date_list, format=str):
    # Extract the unique year and month combinations
    year_month_set = {date[:7].replace('-', '_') for date in date_list}
    # Convert the set to a sorted list
    year_month_list = sorted(list(year_month_set))

    return year_month_list

def process_key_to_retrieve_image(timestamp_list):
    # Create a dictionary to store the grouped timestamps
    grouped_timestamps = defaultdict(list)
    #grouped_timestamps = dict()

    # Iterate over each timestamp
    for timestamp in timestamp_list:
        # Split the timestamp into date and time
        date, time = timestamp.split(' ')
        # Further split the date into year, month, and day
        year, month, day = date.split('-')
        # Format the year and month as 'YYYY - MM'
        year_month = f'{year}_{month}'
        # Format the day and time as 'DD_HH_MM'
        day_time = f'{day}_{time.replace(":", "_")}'
        day_time = day_time[:-3]
        # Append the day_time to the corresponding year_month list
        grouped_timestamps[year_month].append(day_time)

    # Convert the defaultdict to a regular dictionary
    grouped_timestamps = dict(grouped_timestamps)
    return grouped_timestamps

def delete_temp_img_files(folder_path):
    for filename in os.listdir(folder_path):
        # Check if the file is a .png or .jpg
        if filename.endswith('.png') or filename.endswith('.jpg'):
            # Create the full path to the file
            file_path = os.path.join(folder_path, filename)
            # Remove the file
            os.remove(file_path)