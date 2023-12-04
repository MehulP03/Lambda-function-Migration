import json
import boto3
import requests
import os

def create_function(function_name,function_timeout, function_handler, function_runtime):
    sts_connection = boto3.client('sts')
    acct_b = sts_connection.assume_role(
        RoleArn="arn of the other account lambda role giving full access to the source account ",  # lambda account role
        RoleSessionName="cross-acct_lambda"
    )

    ACCESS_KEY = acct_b['Credentials']['AccessKeyId']
    SECRET_KEY = acct_b['Credentials']['SecretAccessKey'] 
    SESSION_TOKEN = acct_b['Credentials']['SessionToken']
    client = boto3.client(
        'lambda',
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        aws_session_token=SESSION_TOKEN,
        region_name="ap-south-1"
    )
    try:
        client.create_function(
            FunctionName=function_name,
            Timeout=function_timeout,
            Handler=function_handler,
            Runtime=function_runtime,
            Role="arn of the lambda role that has the only execute permission",  # resp_gf["Configuration"]["Role"],
            Code={'ZipFile': open('./' + function_name + '.zip', 'rb').read()}
        )
        os.remove('./' + function_name + '.zip')
        print("Create Function: " + function_name)
    except Exception as e:
        print("A problem occurred while creating function : " + function_name + "-----" + str(e))


def get_function_from_source():
    source_session = boto3.Session()  # update with profile name you have for your account at .aws/credentials location
    source_lambda_client = source_session.client('lambda')  # make sure you have defined region as well in your profile definition
    paginator = source_lambda_client.get_paginator('list_functions')
    response_iterator = paginator.paginate()
    for response in response_iterator:
        functions = response["Functions"]
        for function in functions:
            function_name = str(function["FunctionName"])
            function_timeout = function["Timeout"]
            function_handler = function["Handler"]
            function_runtime = function["Runtime"]
            # Export configuration
            export_lambda_configuration(source_lambda_client, function_name)
            # Export code
            export_lambda_code(source_lambda_client, function_name)
            # Create function in the target account
            create_function(function_name, function_timeout, function_handler, function_runtime)


def export_lambda_configuration(lambda_client, function_name):
    response = lambda_client.get_function(FunctionName=function_name)
    with open('./' + function_name + '_config.json', 'w') as config_file:
        config_file.write(json.dumps(response['Configuration'], indent=2))


def export_lambda_code(lambda_client, function_name):
    func_details = lambda_client.get_function(FunctionName=function_name)
    zip_file='./' + function_name + '.zip'
    code_data = func_details['Code']['Location']

    r = requests.get(code_data)
    with open(zip_file, 'wb') as code:
        code.write(r.content)


if __name__ == "__main__":
    get_function_from_source()