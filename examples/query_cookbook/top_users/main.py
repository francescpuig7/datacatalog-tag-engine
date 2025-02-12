# Copyright 2022 Google, LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import hashlib
import base64
import json

from google.cloud import bigquery
bq = bigquery.Client()

def event_handler(request):
    request_json = request.get_json()
    print('request_json:', request_json)
    
    project = request_json['calls'][0][0].strip()
    print('project:', project)
    
    dataset = request_json['calls'][0][1].strip()
    print('dataset:', dataset)
    
    table = request_json['calls'][0][2].strip()
    print('table:', table)
    
    region = request_json['calls'][0][3].strip()
    print('region:', region)
    
    max_users = request_json['calls'][0][4]
    print('max_users:', max_users)
    
    if request_json['calls'][0][5]:
        excluded_accounts = request_json['calls'][0][5]
        print('excluded_accounts:', excluded_accounts)
    else:
        excluded_accounts = None
    
    try:
        html_results = process_query_log(project, dataset, table, region, max_users, excluded_accounts)
        return json.dumps({"replies": [html_results]})
    
    except Exception as e:
        print("Exception caught: " + str(e))
        return json.dumps({"errorMessage": str(e)}), 400 

    
def process_query_log(project, dataset, table, region, max_users, excluded_accounts=None):
    
    print('enter process_query_log')
    
    sql = "select user_email, count(*) "
    sql += "from `" + project + "`.`region-" + region + "`.INFORMATION_SCHEMA.JOBS_BY_PROJECT, unnest(referenced_tables) as rf "
    sql += "where statement_type = 'SELECT' "
    sql += "and query not like '%INFORMATION_SCHEMA%' "
    sql += "and state = 'DONE' "
    sql += "and error_result is null "
    sql += "and rf.project_id = '" + project + "' "
    sql += "and rf.dataset_id = '" + dataset + "' "
    sql += "and rf.table_id = '" + table + "'" 
       
    if excluded_accounts:
        sql += " and user_email not in ("
        
        index = 0
        
        for account in excluded_accounts:
            
            if index > 0:
                sql += ","
            
            sql += "'" + account + "'"
            
            index += 1
            
        sql += ")"
        
    sql += " group by user_email "
    sql += " order by count(*) desc "
    sql += " limit " + str(max_users)
    print(sql)
    
    query_job = bq.query(sql)  
    results = query_job.result()
    html_results = '<html>'
      
    for result in results:
        user_email = result.user_email
        html_results += user_email + '<br>'

    html_results += '</html>'
    print('html_results:', html_results)
            
    return html_results       