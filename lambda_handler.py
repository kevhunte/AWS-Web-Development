import boto3, json, uuid, sys
from boto3.dynamodb.conditions import Key, Attr

s3 = boto3.client('s3')
s3Bucket = boto3.resource('s3')
dynamodb = boto3.resource('dynamodb')

#this dict is used for the configuring courts dynamic dropdown list
#State, acronym, parent_id
states = {
    "0":["Alabama", "AL",'53'],
    "1":["Alaska","AK",'55'],
    "2":["Arizona","AZ",'57'],
    "3":["Arkansas","AR",'59'],
    "4":["California","CA",'61'],
    "5":["Colorado","CO",'63'],
    "6":["Connecticut","CT",'65'],
    "7":["Delaware","DE",'67'],
    "8":["Florida","FL",'69'],
    "9":["Georgia","GA",'71'],
    "10":["Hawaii","HI",'73'],
    "11":["Idaho","ID",'75'],
    "12":["Illinois","IL",'77'],
    "13":["Indiana","IN",'79'],
    "14":["Iowa","IA",'81'],
    "15":["Kansas","KS",'83'],
    "16":["Kentucky","KY",'85'],
    "17":["Louisiana","LA",'87'],
    "18":["Maine","ME",'89'],
    "19":["Maryland","MD",'91'],
    "20":["Massachusetts","MA",'93'],
    "21":["Michigan","MI",'95'],
    "22":["Minnesota","MN",'97'],
    "23":["Mississippi","MS",'99'],
    "24":["Missouri","MO",'101'],
    "25":["Montana","MT",'103'],
    "26":["Nebraska","NE",'105'],
    "27":["Nevada","NV",'107'],
    "28":["New Hampshire","NH",'109'],
    "29":["New Jersey","NJ",'111'],
    "30":["New Mexico","NM",'113'],
    "31":["New York","NY",'115'],
    "32":["North Carolina","NC",'117'],
    "33":["North Dakota","ND",'119'],
    "34":["Ohio","OH",'121'],
    "35":["Oklahoma","OK",'123'],
    "36":["Oregon","OR",'125'],
    "37":["Pennsylvania","PA",'127'],
    "38":["Rhode Island","RI",'129'],
    "39":["South Carolina","SC",'131'],
    "40":["South Dakota","SD",'133'],
    "41":["Tennessee","TN",'135'],
    "42":["Texas","TX",'137'],
    "43":["Utah","UT",'139'],
    "44":["Vermont","VT",'141'],
    "45":["Virginia","VA",'143'],
    "46":["Washington","WA",'145'],
    "47":["West Virginia","WV",'147'],
    "48":["Wisconsin","WI",'149'],
    "49":["Wyoming","WY",'151'],
    "50":["District of Columbia","DC",'153'],
    "51":["Puerto Rico","PR",'155']
}

return_val = {
            "message":"Submission Successful"
        }
        
def sortDict(dictionary_list):
    newlist = sorted(dictionary_list, key=lambda k: k['name'])
    return newlist

def jsonToDB(data):
    print('jsonToDB: loading json into database...')        #logs
    s3.download_file('','webpages/case_names.json','/tmp/temp.json')
    f = open('/tmp/temp.json','r')
    dict_list = json.load(f)
    f.close()
    table = dynamodb.Table('')  #fill in table name
    update_case = False
    caseID = str(uuid.uuid4())      #generates random ID for every case
    #reformat dates to look like html version
    if('/' in data['Filed']):
        result = data.pop('Filed').split('/')
        new_date = result[2]+'-'+result[0]+'-'+result[1]
        print('new date: '+new_date)
        data['Filed'] = new_date
    #print('Case ID: ', caseID)
    if('Case ID' in data):           #for updating cases
        #data.pop('update') 
        ID = data['Case ID']        
        response = table.scan(
                FilterExpression=Attr('Case ID').contains(ID)
                )
        item = response['Items']    #returns exact case
        if item:
            table.delete_item(      #These are the keys, should be same for data and item
                Key={
                    "FullName":item['FullName'],
                    "Party":item['Party'],
                    "Case ID":item['Case ID']
                }
            )
            item.update(data)       #updates item with new vals from user
            table.put_item(Item=item)
            new = {}
            new['name']=str(data['FullName'])
            dict_list.append(new)
            dict_list = sortDict(dict_list)
            print('result', str(dict_list))
            f = open('/tmp/temp.json','w')      #opening with r+ does not work properly
            json.dump(dict_list,f, indent=4,sort_keys=True)
            f.close()
            s3Bucket.Bucket('').upload_file('/tmp/temp.json','webpages/case_names.json', ExtraArgs={"CacheControl":"no-cache, no-store"})
    else:                           #new cases
        data['Case ID'] = caseID
        if('Excel_tag' in data):      #getting rid of/reformatting certain values
            data.pop('Excel_tag')
        if('State Code' in data):
            if('Skip to Schedule J' in data['State Code']):
                data.pop('State Code')
        if('court' in data):
            data['Jurisdiction']=data.pop('court')
        if('Phoenix Attorney' in data):
            data['Nassau Attorney'] = data.pop('Phoenix Attorney')
        table.put_item(Item=data) #may be a source of injection, add more logic here
        new = {}
        new['name']=str(data['FullName'])
        dict_list.append(new)
        dict_list = sortDict(dict_list)
        print('result', str(dict_list))
        f = open('/tmp/temp.json','w')      #opening with r+ does not work properly
        json.dump(dict_list,f, indent=4,sort_keys=True)
        f.close()
        s3Bucket.Bucket('').upload_file('/tmp/temp.json','webpages/case_names.json', ExtraArgs={"CacheControl":"no-cache, no-store"})
    print('jsonToDB: Case upload successful')
    #f = open('form_success.html','r')
    #return html file when API gateway problem is fixed
    #f.read().encode()
    global return_val
    return_val = {
        "message": "Form Uploaded successfully"
    }

def rangedDateQuery(keyName,start,end):
    filtExp = (Attr(keyName).contains(start) | (Attr(keyName).gt(start) & Attr(keyName).lt(end)) | Attr(keyName).contains(end)) #first val. now iterate through
    return filtExp
    
def rangedAmountQuery(amount,LorG):
    if('less' in LorG):
        filtExp = (Attr('Amount Dispute').contains(amount) | Attr('Amount Dispute').lt(amount))
    else:
        filtExp = (Attr('Amount Dispute').contains(amount) | Attr('Amount Dispute').gt(amount))
    return filtExp
        
def dataBaseSearch(data):
    print('dataBaseSearch: starting...')     #logs
    update_case = False
    table = dynamodb.Table('')
    keyword = data['Keyword']
    if(keyword):       #if not empty and lower case
        if(not keyword[0].isupper()):
            keyword = keyword.capitalize()
    keyword_filtExp = (Attr('FullName').contains(keyword) | Attr('Party').contains(keyword) | Attr('Jurisdiction').contains(keyword) | Attr('Category').contains(keyword) | Attr('PolicyNo').contains(keyword) | Attr('Sub Category').contains(keyword) | Attr('Short Name').contains(keyword) | Attr('Nassau Attorney').contains(keyword) | Attr('Phoenix Attorney').contains(keyword))
    case_status = data['Open/Closed']
    case_status_filtExp = (Attr('Open/Closed').contains(case_status) | Attr('status').contains(case_status))
    Plaintiff_Defendant = data['Plaintiff/Defendant']
    Plaintiff_Defendant_filtExp = (Attr('Plaintiff_Defendant').contains(Plaintiff_Defendant) | Attr('Plaintiff/ Defendant').contains(Plaintiff_Defendant))
    Amount = data['Amount_Dispute']
    Amount_LessorGreater = data['Less/Greater']
    Amount_filtExp = rangedAmountQuery(Amount,Amount_LessorGreater)
    FAS5 = data['FAS_5']
    FAS5_filtExp = Attr('FAS5').contains(FAS5)
    Schedule_F = data['Schedule_F']
    Schedule_F_filtExp = Attr('Schedule F').contains(Schedule_F)
    Schedule_J = data['Schedule_J']
    Schedule_J_filtExp = Attr('Schedule J').contains(Schedule_J)
    Sig_matter = data['Significant']
    Sig_matter_filtExp = Attr('Significant').contains(Sig_matter)
    policyNum = data['policyNo']
    policyNum_filtExp = Attr('policyNo').contains(policyNum)
    fClosing_date = data['fromClosingDate']
    tClosing_date = data['toClosingDate']
    if(fClosing_date and tClosing_date):
        Closing_date_filtExp = rangedDateQuery('Close Date',fClosing_date,tClosing_date)
    fFiling_date = data['fromFilingDate']
    tFiling_date = data['toFilingDate']
    if(fFiling_date and tFiling_date):
        Filing_date_filtExp = rangedDateQuery('Filed',fFiling_date,tFiling_date)
    if(data):
        print('searching for: '+str(data))
        if(Plaintiff_Defendant):
            if(keyword):
                response = table.scan(
                FilterExpression=keyword_filtExp & case_status_filtExp & Plaintiff_Defendant_filtExp
                )
            else:
                response = table.scan(
                FilterExpression=case_status_filtExp & Plaintiff_Defendant_filtExp
                )
        elif(Amount):
            if(keyword):
                response = table.scan(
                FilterExpression=keyword_filtExp & case_status_filtExp & Amount_filtExp
                )
            else:
                response = table.scan(
                FilterExpression=case_status_filtExp & Amount_filtExp
                )
        elif(FAS5):
            if(keyword):
                response = table.scan(
                FilterExpression=keyword_filtExp & case_status_filtExp & FAS5_filtExp
                )
            else:
                response = table.scan(
                FilterExpression=case_status_filtExp & FAS5_filtExp
                )
        elif(Schedule_F):
            if(keyword):
                response = table.scan(
                FilterExpression=keyword_filtExp & case_status_filtExp & Schedule_F_filtExp
                )
            else:
                response = table.scan(
                FilterExpression=case_status_filtExp & Schedule_F_filtExp
                )
        elif(Schedule_J):
            if(keyword):
                response = table.scan(
                FilterExpression=keyword_filtExp & case_status_filtExp & Schedule_J_filtExp
                )
            else:
                response = table.scan(
                FilterExpression=case_status_filtExp & Schedule_J_filtExp
                )
        elif(Sig_matter):
            if(keyword):
                response = table.scan(
                FilterExpression=keyword_filtExp & case_status_filtExp & Sig_matter_filtExp
                )
            else:
                response = table.scan(
                FilterExpression=case_status_filtExp & Sig_matter_filtExp
                )
        elif(policyNum):
            if(keyword):
                response = table.scan(
                FilterExpression=keyword_filtExp & case_status_filtExp & policyNum_filtExp
                )
            else:
                response = table.scan(
                FilterExpression=case_status_filtExp & policyNum_filtExp
                )
        elif(tClosing_date and fClosing_date):
            if(keyword):
                response = table.scan(
                FilterExpression=keyword_filtExp & case_status_filtExp & Closing_date_filtExp
                )
            else:
                response = table.scan(
                FilterExpression=case_status_filtExp & Closing_date_filtExp
                )
        elif(tFiling_date and fFiling_date):
            if(keyword):
                response = table.scan(
                FilterExpression=keyword_filtExp & case_status_filtExp & Filing_date_filtExp
                )
            else:
                response = table.scan(
                FilterExpression=case_status_filtExp & Filing_date_filtExp
                )
        else:                          #case_status always set, can be default search
            if(keyword):
                response = table.scan(
                FilterExpression=keyword_filtExp & case_status_filtExp
                )
            else:
                response = table.scan(
                FilterExpression=case_status_filtExp
                )
        items = response['Items']
        caseNames = []
        if items:
            if(update_case): #this will send all the case information
                caseNames.append(items)
            else:
                for i in items:
                    #caseNames.append('Case Name: '+i['FullName']+', Case Status: '+i['Open/Closed']+', Party: '+i['Party']+', Case ID: '+i['Case ID'])
                    caseNames.append(i)     #returns all case 
        print('returned case(s):')
        for n in caseNames:
            print(n)
    global return_val
    #return_val = items
    return_val = {}
    for i in range(0,len(caseNames)):
        val = 'Case '+str(i+1)
        return_val[val] = caseNames[i]


def lambda_handler(event, context):
    
    """
    #####
    This function logs events in AWS CloudWatch
    #####
    """
    if event:
        print('Event: ', str(event))    #logs
        
        if('body-json' in event and 'POST' in event['context']['http-method']):
            #new case uploads
            data=event['body-json']    #list of json objects
            #print('datatype: ',str(type(data)))
            if(str(type(data)) == "<class 'dict'>"): #case coming from HTML form
                processed_data = {}
                for k in data:              
                    if(not k['value']):    #empty values cannot be put in datatables
                        continue
                    elif(str(k['name']) in processed_data.keys()):  #key already in dict, save both vals
                        vals = []
                        vals.append(processed_data.pop(k['name'])) #gets old val
                        vals.append(k['value'])                 #adds on new val
                        print('multiple vals: ',str(vals))
                        processed_data[k['name']] = vals
                        #processed_data[k['name']]= (k['value'], processed_data.pop(k['name']))
                    else:
                        processed_data[k['name']] = k['value']
                print('processed data: ',processed_data) #logs
                jsonToDB(processed_data)
            elif(str(type(data)) == "<class 'list'>"): #case coming from excel sheet
                data_list = []
                #processed_data = {}
                if('undefined' in data[0]):    #working file for courts dynamic dropdown list
                    myFile = open("/tmp/state_level_court_Updated.json","a") #rewrite the list each time
                    index = 0
                    for i in range(0,52):       #populates file with state info
                        state = str(states.get(str(i))[0])
                        info = {}
                        info["id"]= str(index+1)
                        info["name"]= state
                        info["parent_id"]="0"
                        data_list.append(info)
                        #json.dump(info,myFile, indent=4,sort_keys=True) 
                        index+=1
                    for j in range(1,53):       #populates file with corresponding state/fed ID
                        info = {}
                        info["id"]= str(index+1)
                        info["name"]= "State"
                        info["parent_id"]=str(j)
                        info2 = {}
                        index+=1
                        info2["id"]= str(index+1)
                        info2["name"]= "Federal"
                        info2["parent_id"]=str(j)
                        data_list.append(info)
                        data_list.append(info2)
                        #json.dump(info,myFile, indent=4,sort_keys=True)
                        #json.dump(info2,myFile, indent=4,sort_keys=True)
                        index+=1
                        prev_state = "AL"   #first state, will be default
                        state_iterator = 0  #used to return state info
                    for d in data:
                        #print('writing: ',d)    #logging. d is a dict datatype
                        d['id'] = str(index+1)
                        if 'State Court (S)' in d:
                            court = d.pop('State Court (S)')
                            if '(S)' in court:
                                court.replace('(S)', '')
                            elif '(F)' in court:
                                court.replace('(F)', '')
                            d['name'] = court
                            if(prev_state != d['name'].split()[0] and len(d['name'].split()[0]) < 3): #different state
                                state_iterator+=1
                                prev_state = d['name'].split()[0]
                            if(state_iterator<52):
                                d['parent_id'] = states[str(state_iterator)][2] #match id w/ state
                            if 'Federal Court (S)' in d or 'Federal Court (F)' in d or 'Federal Court - (F)' in d or 'Federal Court  - (F)' in d:
                                fed_case = {}
                                fed_case["id"] = str(index+2)
                                if 'Federal Court (S)' in d:
                                    court = d.pop('Federal Court (S)')
                                    if '(S)' in court:
                                        court.replace('(S)', '')
                                    elif '(F)' in court:
                                        court.replace('(F)', '')
                                    fed_case['name'] = court
                                    #fed_case['name'] = d.pop('Federal Court (S)').replace('(S)', '') #gets of (S) and (F)
                                    #print (fed_case['name'],' popped from d')   #debugging
                                elif 'Federal Court (F)' in d:
                                    court = d.pop('Federal Court (F)')
                                    if '(S)' in court:
                                        court.replace('(S)', '')
                                    elif '(F)' in court:
                                        court.replace('(F)', '')
                                    fed_case['name'] = court
                                    #fed_case['name'] = d.pop('Federal Court (F)').replace('(F)', '')
                                    #print (fed_case['name'],' popped from d')   #debugging
                                elif 'Federal Court - (F)' in d:
                                    court = d.pop('Federal Court - (F)')
                                    if '(S)' in court:
                                        court.replace('(S)', '')
                                    elif '(F)' in court:
                                        court.replace('(F)', '')
                                    fed_case['name'] = court
                                    #fed_case['name'] = d.pop('Federal Court - (F)').replace('(F)', '')
                                elif 'Federal Court  - (F)' in d:
                                    court = d.pop('Federal Court  - (F)')
                                    if '(S)' in court:
                                        court.replace('(S)', '')
                                    elif '(F)' in court:
                                        court.replace('(F)', '')
                                    fed_case['name'] = court
                                    #fed_case['name'] = d.pop('Federal Court  - (F)').replace('(F)', '')
                                fed_case["parent_id"] = str(int(states[str(state_iterator)][2])+1)
                                #print("Court Name: ",fed_case['name'])      #debugging
                                data_list.append(fed_case)
                        elif 'State Court - (S)' in d:
                            d['name'] = d.pop('State Court - (S)').replace('(S)', '')
                            if(prev_state != d['name'].split()[0] and len(d['name'].split()[0]) < 3): #different state
                                state_iterator+=1
                                prev_state = d['name'].split()[0]
                            if(state_iterator<52):
                                d['parent_id'] = states[str(state_iterator)][2] #match id w/ state
                            if 'Federal Court (S)' in d or 'Federal Court (F)' in d or 'Federal Court - (F)' in d or 'Federal Court  - (F)' in d:
                                fed_case = {}
                                fed_case["id"] = str(index+2)
                                if 'Federal Court (S)' in d:
                                    court = d.pop('Federal Court (S)')
                                    if '(S)' in court:
                                        court.replace('(S)', '')
                                    elif '(F)' in court:
                                        court.replace('(F)', '')
                                    fed_case['name'] = court
                                    #fed_case['name'] = d.pop('Federal Court (S)').replace('(S)', '')
                                elif 'Federal Court (F)' in d:
                                    court = d.pop('Federal Court (F)')
                                    if '(S)' in court:
                                        court.replace('(S)', '')
                                    elif '(F)' in court:
                                        court.replace('(F)', '')
                                    fed_case['name'] = court
                                    #fed_case['name'] = d.pop('Federal Court (F)').replace('(F)', '')
                                elif 'Federal Court - (F)' in d:
                                    court = d.pop('Federal Court - (F)')
                                    if '(S)' in court:
                                        court.replace('(S)', '')
                                    elif '(F)' in court:
                                        court.replace('(F)', '')
                                    fed_case['name'] = court
                                    #fed_case['name'] = d.pop('Federal Court - (F)').replace('(F)', '')
                                elif 'Federal Court  - (F)' in d:
                                    court = d.pop('Federal Court  - (F)')
                                    if '(S)' in court:
                                        court.replace('(S)', '')
                                    elif '(F)' in court:
                                        court.replace('(F)', '')
                                    fed_case['name'] = court
                                    #fed_case['name'] = d.pop('Federal Court  - (F)').replace('(F)', '')
                                fed_case["parent_id"] = str(int(states[str(state_iterator)][2])+1)
                                #print("Court Name: ",fed_case['name'])      #debugging
                                data_list.append(fed_case)
                        if 'undefined' in d:
                            d.pop('undefined')  #cleaning json
                        #get parent_id of each state to match. find cond to inc state_iterator
                        index+=1
                        data_list.append(d)
                    json.dump(data_list,myFile, indent=4,sort_keys=True)
                    myFile.close()
                    #rewrites state_level_court.json file in bucket
                    s3Bucket.Bucket('').upload_file('/tmp/state_level_court_Updated.json','webpages/state_level_court.json', ExtraArgs={"CacheControl":"no-cache, no-store"})
                    print('added to ** successfully')
                elif('maintenance page' in data[0]):
                    print(data,"Received")
                    if('attorney_update' in data[1]):#download respective file and make changes
                        s3.download_file('','webpages/in_house_attorney.json','/tmp/temp.json')
                        f = open('/tmp/temp.json','r')
                        dict_list = json.load(f)
                        f.close()
                        if('add' in data[3]):
                            if(data[2]):        #check if contains value first
                                new = {}
                                new['id']="0"
                                new['name']=str(data[2])
                                new['parent_id']='0'
                                dict_list.append(new)
                                dict_list = sortDict(dict_list)
                                #print('result', str(dict_list))
                                f = open('/tmp/temp.json','w')      #opening with r+ does not work properly
                                json.dump(dict_list,f, indent=4,sort_keys=True)
                                f.close()
                                s3Bucket.Bucket('').upload_file('/tmp/temp.json','webpages/in_house_attorney.json', ExtraArgs={"CacheControl":"no-cache, no-store"})
                        elif('edit' in data[3]):
                            if(data[2] and data[4]):        #check if contains value first
                                result = [val for val in dict_list if not (val['name'] == data[2])] #deletes old item
                                new = {}
                                new['id']="0"
                                new['name']=str(data[4])
                                new['parent_id']='0'
                                result.append(new)
                                result = sortDict(result)
                                print('result', str(result))
                                f = open('/tmp/temp.json','w')      #opening with r+ does not work properly
                                json.dump(result,f, indent=4,sort_keys=True)
                                f.close()
                                s3Bucket.Bucket('').upload_file('/tmp/temp.json','webpages/in_house_attorney.json', ExtraArgs={"CacheControl":"no-cache, no-store"})
                        elif('delete' in data[3]):#find data[1] and delete object
                            result = [val for val in dict_list if not (val['name'] == data[2])] #removes value from list
                            print('result', str(result))
                            f = open('/tmp/temp.json','w')
                            json.dump(result,f,indent=4,sort_keys=True)
                            f.close()
                            s3Bucket.Bucket('').upload_file('/tmp/temp.json','webpages/in_house_attorney.json', ExtraArgs={"CacheControl":"no-cache, no-store"})
                    elif('party_update' in data[1]):
                        s3.download_file('','webpages/nassau_party.json','/tmp/temp.json')
                        f = open('/tmp/temp.json','r')
                        dict_list = json.load(f)
                        f.close()
                        #print('data: ',str(dict_list))
                        if('add' in data[3]):
                            if(data[2]):        #check if contains value first
                                new = {}
                                new['id']="0"
                                new['name']=str(data[2])
                                new['parent_id']='0'
                                dict_list.append(new)
                                dict_list = sortDict(dict_list)
                                print('result', str(dict_list))
                                f = open('/tmp/temp.json','w')      #opening with r+ does not work properly
                                json.dump(dict_list,f, indent=4,sort_keys=True)
                                f.close()
                                s3Bucket.Bucket('').upload_file('/tmp/temp.json','webpages/nassau_party.json', ExtraArgs={"CacheControl":"no-cache, no-store"})
                        elif('edit' in data[3]):
                            if(data[2] and data[4]):        #check if contains value first
                                result = [val for val in dict_list if not (val['name'] == data[2])] #deletes old item
                                new = {}
                                new['id']="0"
                                new['name']=str(data[4])
                                new['parent_id']='0'
                                result.append(new)
                                result = sortDict(result)
                                print('result', str(result))
                                f = open('/tmp/temp.json','w')      #opening with r+ does not work properly
                                json.dump(result,f, indent=4,sort_keys=True)
                                f.close()
                                s3Bucket.Bucket('').upload_file('/tmp/temp.json','webpages/nassau_party.json', ExtraArgs={"CacheControl":"no-cache, no-store"})
                        elif('delete' in data[3]):#find data[2] and delete object
                            result = [val for val in dict_list if not (val['name'] == data[2])] #removes value from list
                            print('result', str(result))
                            f = open('/tmp/temp.json','w')
                            json.dump(result,f,indent=4,sort_keys=True)
                            f.close()
                            s3Bucket.Bucket('').upload_file('/tmp/temp.json','webpages/nassau_party.json', ExtraArgs={"CacheControl":"no-cache, no-store"})
                    elif('matter_update' in data[1]):
                        s3.download_file('','webpages/matter_type.json','/tmp/temp.json')
                        f = open('/tmp/temp.json','r')
                        dict_list = json.load(f)
                        f.close()
                        if('add' in data[3]):
                            if(data[2]):        #check if contains value first
                                new = {}
                                new['id']="0"
                                new['name']=str(data[2])
                                new['parent_id']='0'
                                dict_list.append(new)
                                dict_list = sortDict(dict_list)
                                print('result', str(dict_list))
                                f = open('/tmp/temp.json','w')      #opening with r+ does not work properly
                                json.dump(dict_list,f, indent=4,sort_keys=True)
                                f.close()
                                s3Bucket.Bucket('').upload_file('/tmp/temp.json','webpages/matter_type.json', ExtraArgs={"CacheControl":"no-cache, no-store"})
                        elif('edit' in data[3]):
                            if(data[2] and data[4]):        #check if contains value first
                                result = [val for val in dict_list if not (val['name'] == data[2])] #deletes old item
                                new = {}
                                new['id']="0"
                                new['name']=str(data[4])
                                new['parent_id']='0'
                                result.append(new)
                                result = sortDict(result)
                                print('result', str(result))
                                f = open('/tmp/temp.json','w')      #opening with r+ does not work properly
                                json.dump(result,f, indent=4,sort_keys=True)
                                f.close()
                                s3Bucket.Bucket('').upload_file('/tmp/temp.json','webpages/matter_type.json', ExtraArgs={"CacheControl":"no-cache, no-store"})
                        elif('delete' in data[3]):#find data[2] and delete object
                            result = [val for val in dict_list if not (val['name'] == data[2])] #removes value from list
                            print('result', str(result))
                            f = open('/tmp/temp.json','w')
                            json.dump(result,f,indent=4,sort_keys=True)
                            f.close()
                            s3Bucket.Bucket('').upload_file('/tmp/temp.json','webpages/matter_type.json', ExtraArgs={"CacheControl":"no-cache, no-store"})
                    elif('litigation_hold_update' in data[1]):
                        s3.download_file('','webpages/litigation_hold.json','/tmp/temp.json')
                        f = open('/tmp/temp.json','r')
                        dict_list = json.load(f)
                        f.close()
                        if('add' in data[3]):
                            if(data[2]):        #check if contains value first
                                new = {}
                                new['id']="0"
                                new['name']=str(data[2])
                                new['parent_id']='0'
                                dict_list.append(new)
                                dict_list = sortDict(dict_list)
                                print('result', str(dict_list))
                                f = open('/tmp/temp.json','w')      #opening with r+ does not work properly
                                json.dump(dict_list,f, indent=4,sort_keys=True)
                                f.close()
                                s3Bucket.Bucket('').upload_file('/tmp/temp.json','webpages/litigation_hold.json', ExtraArgs={"CacheControl":"no-cache, no-store"})
                        elif('edit' in data[3]):
                            if(data[2] and data[4]):        #check if contains value first
                                result = [val for val in dict_list if not (val['name'] == data[2])] #deletes old item
                                new = {}
                                new['id']="0"
                                new['name']=str(data[4])
                                new['parent_id']='0'
                                result.append(new)
                                result = sortDict(result)
                                print('result', str(result))
                                f = open('/tmp/temp.json','w')      #opening with r+ does not work properly
                                json.dump(result,f, indent=4,sort_keys=True)
                                f.close()
                                s3Bucket.Bucket('').upload_file('/tmp/temp.json','webpages/litigation_hold.json', ExtraArgs={"CacheControl":"no-cache, no-store"})
                        elif('delete' in data[3]):#find data[2] and delete object
                            result = [val for val in dict_list if not (val['name'] == data[2])] #removes value from list
                            print('result', str(result))
                            f = open('/tmp/temp.json','w')
                            json.dump(result,f,indent=4,sort_keys=True)
                            f.close()
                            s3Bucket.Bucket('').upload_file('/tmp/temp.json','webpages/litigation_hold.json', ExtraArgs={"CacheControl":"no-cache, no-store"})
                    elif('category_update' in data[1]):
                        choice = data[4]
                        if('subcategory' in choice):
                            s3.download_file('','webpages/subCategory.json','/tmp/temp.json')
                        elif('category' in choice):
                            s3.download_file('','webpages/category.json','/tmp/temp.json')
                        f = open('/tmp/temp.json','r')
                        dict_list = json.load(f)
                        f.close()
                        if('add' in data[3]):
                            if(data[2]):        #check if contains value first
                                new = {}
                                new['id']="0"
                                new['name']=str(data[2])
                                new['parent_id']='0'
                                dict_list.append(new)
                                dict_list = sortDict(dict_list)
                                print('result', str(dict_list))
                                f = open('/tmp/temp.json','w')      #opening with r+ does not work properly
                                json.dump(dict_list,f, indent=4,sort_keys=True)
                                f.close()
                                if('subcategory' in choice):
                                    s3Bucket.Bucket('').upload_file('/tmp/temp.json','webpages/subCategory.json', ExtraArgs={"CacheControl":"no-cache, no-store"})
                                elif('category' in choice):
                                    s3Bucket.Bucket('').upload_file('/tmp/temp.json','webpages/category.json', ExtraArgs={"CacheControl":"no-cache, no-store"})
                        elif('edit' in data[3]):
                            if(data[2] and data[4]):        #check if contains value first
                                result = [val for val in dict_list if not (val['name'] == data[2])] #deletes old item
                                new = {}
                                new['id']="0"
                                new['name']=str(data[4])
                                new['parent_id']='0'
                                result.append(new)
                                result = sortDict(result)
                                print('result', str(result))
                                f = open('/tmp/temp.json','w')      #opening with r+ does not work properly
                                json.dump(result,f, indent=4,sort_keys=True)
                                f.close()
                                if('subcategory' in choice):
                                    s3Bucket.Bucket('').upload_file('/tmp/temp.json','webpages/subCategory.json', ExtraArgs={"CacheControl":"no-cache, no-store"})
                                elif('category' in choice):
                                    s3Bucket.Bucket('').upload_file('/tmp/temp.json','webpages/category.json', ExtraArgs={"CacheControl":"no-cache, no-store"})
                        elif('delete' in data[3]):
                            result = [val for val in dict_list if not (val['name'] == data[2])] #removes value from list
                            print('result', str(result))
                            f = open('/tmp/temp.json','w')
                            json.dump(result,f,indent=4,sort_keys=True)
                            f.close()
                            if('subcategory' in choice):
                                s3Bucket.Bucket('').upload_file('/tmp/temp.json','webpages/subCategory.json', ExtraArgs={"CacheControl":"no-cache, no-store"})
                            elif('category' in choice):
                                s3Bucket.Bucket('').upload_file('/tmp/temp.json','webpages/category.json', ExtraArgs={"CacheControl":"no-cache, no-store"})
                else:
                    processed_data = {}
                    for d in data:
                        if ('Full Name' in d):    #for excel uploads. These keys are incorrect
                            d['FullName'] = d.pop('Full Name')
                        if ('Amount in Dispute' in d):
                            d['Amount Dispute'] = d.pop(' Amount in Dispute ')
                        if ('Business Contact' in d):
                            d['Business_Contact'] = d.pop('Business Contact')
                        if ('Open/Closed' not in d):
                            d['Open/Closed'] = 'Open' #default for new cases
                        
                        if(not d['value']):    #empty values cannot be put in datatables
                            continue
                        elif(d['name'] in processed_data.keys()):  #key already in dict, save both vals
                            vals = []
                            vals.append(processed_data.pop(d['name'])) #gets old val
                            vals.append(d['value'])                 #adds on new val
                            #print('multiple vals: ',str(vals))
                            processed_data[d['name']] = vals
                        else:
                            processed_data[d['name']] = d['value']
                            if('state' in processed_data):  #cleaning dict
                                processed_data.pop('state')
                            elif('state_federal' in processed_data):
                                processed_data.pop('state_federal')
                    print('processed data: ',processed_data) #logs
                    jsonToDB(processed_data)
        elif('body-json' in event and 'GET' in event['context']['http-method']):
            #case searches
            data=event['params']['querystring']
            dataBaseSearch(data)
        
        elif('Records' in event):
            #change made to webserver
            fname=event['Records'][0]['s3']['object']['key']
            bucket=event['Records'][0]['s3']['bucket']['name']
            print(fname+' was added to '+bucket)    #logs
           
            
        return return_val
