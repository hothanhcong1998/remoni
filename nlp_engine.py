import os
import pandas as pd
import json
from datetime import datetime
from config_nlp_engine_new import SYSTEM_PROMPT_INTENT_DETECTION, \
                                  SYSTEM_PROMPT_VISION, \
                                  SYSTEM_PROMPT_ENDPOINT, \
                                  TEXT_ENDPOINT_FORMAT, \
                                  SYSTEM_PROMPT_MEDICAL, \
                                  INPUT_VISION

from utils import *
from request_to_openai import gpt, gpt_med

system_prompt_intent_detection = SYSTEM_PROMPT_INTENT_DETECTION #.format(current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
system_prompt_vision = SYSTEM_PROMPT_VISION
system_prompt_endpoint = SYSTEM_PROMPT_ENDPOINT
text_endpoint_format =  TEXT_ENDPOINT_FORMAT 
#.format(patient_id, name, sex, address, phone, dob, age, image_description, vital_signs_data, question)

patient_meta_df = pd.read_csv('./static/local_data/fake_patient_meta_data.csv')

class nlp_engine():

    def __init__(self):
        self.patient_id = None
        self.image_description = 'None'
        self.vital_signs_text = 'None' 
        self.show_data_list = []
        self.intent_dict = {}
        self.patient_meta_df = pd.read_csv('./static/local_data/fake_patient_meta_data.csv')

    def intent_detection(self, doctor_question):
        if not doctor_question:
            return False

        intent = gpt(
            system_prompt=SYSTEM_PROMPT_INTENT_DETECTION.format(current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")), \
            text=doctor_question, \
            model_name="gpt-3.5-turbo", \
            temperature=0.1
            )
        intent_dict = json.loads(intent)
        self.intent_dict = intent_dict

        print('=========INTENT==========')
        print(intent_dict)
        return True

    def vision_llm(self, image_path_list: list):
        print('==== IMAGE PATH LIST ====')
        print(image_path_list)

        if not image_path_list:
            self.image_description = 'Can not get image data'
            return self.image_description
        for image_path in image_path_list:
            if not os.path.exists(image_path):
                return 'Can not find image'

        image_description = gpt(
            text = INPUT_VISION,
            model_name="gpt-4-vision-preview", 
            image_path = image_path_list, ############################# TODO: change image path  ############################
            system_prompt = SYSTEM_PROMPT_VISION,
            temperature = 0.4
        ) 
        self.image_description = image_description
        return self.image_description

    def endpoint_llm (self, patient_info, doctor_question):
        text_endpoint = TEXT_ENDPOINT_FORMAT.format(
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            patient_id = self.patient_id,
            name = patient_info['name'].values[0], 
            sex = patient_info['sex'].values[0], 
            address = patient_info['address'].values[0], 
            phone = patient_info['phone'].values[0], 
            dob = patient_info['birth'].values[0], 
            age = patient_info['age'].values[0], 
            image_description = self.image_description, 
            vital_signs_data = self.vital_signs_text, 
            question = doctor_question,
            temperature = 0.5
        )

        print('=========TEXT ENDPOINT==========')
        print(text_endpoint)

        output = gpt(
            system_prompt=SYSTEM_PROMPT_ENDPOINT, 
            text=text_endpoint, 
            model_name="gpt-3.5-turbo", 
            temperature=0.2
        )
        return output

    def patient_llm(self, patient_conv):
        print('=========PATIENT-SIDE INTERACTION==========')
        #print(patient_conv)

        output = gpt_med(
            system_prompt=SYSTEM_PROMPT_MEDICAL, 
            text=patient_conv, 
            model_name="gpt-3.5-turbo", 
            temperature=0.2
        )
        return output

    # check if the id_str is a valid patient id
    def _is_valid_id(self):
        if bool(re.match(r'^\d{5}$', self.intent_dict['patient_id'])): #check if the id_str follow id format
            if int(self.intent_dict['patient_id']) in self.patient_meta_df['patient_id'].values: # check if the id_str appears in the current database
                return True
            else: return False        
        else: return False


    # return the valid id to retrieve patient data    
    def _ask_for_id(self): # TODO: need to be updated to capable of working with flask
        while True:
            # ask user to provide the valid id
            temp = input('I did not receive a valid patient ID number. Please provide a valid ID number.')
            
            if temp == '':  # if the user cannot provide a valid patient_id, the session will stop
                return False
            
            temp_patient_id = extract_patient_id_from_text(temp) 
            
            if is_valid_id(temp_patient_id, self.patient_meta_df):
                break

        return temp_patient_id


    def check_and_update_patient_id(self):
        # check if there is a valid patient_id in the intent => update self.patient_id
        if self._is_valid_id():
                self.patient_id = self.intent_dict['patient_id']
        else:
            # check if self.patient_id is null
            if not self.patient_id:
                #new_id = self._ask_for_id()
                return False
                #if not new_id: return False  # if the user cannot provide a valid patient_id, the session will stop
                #else: 
                #    self.patient_id = new_id
                #    self.intent_dict['patient_id'] = new_id
        return True
    
    
    def process_special_historical_data_retrieval(self):
        if (len(self.intent_dict['list_date']) == 0) and (len(self.intent_dict['list_time']) == 0): 
            return
        # process some special case
        if len(self.intent_dict['list_date']) == 0: # the patient ask for data in some sessions in the current day, ex. today morning, this evening
            self.intent_dict['list_date'] = [datetime.now().strftime("%Y-%m-%d")]
        
        if len(self.intent_dict['list_time']) == 0:  # the patient ask for data in some day without providing the time, ex. last 3 days, last week
            self.intent_dict['list_time'] = ['01:00:00', '07:00:00', '13:00:00', '19:00:00']
                   
