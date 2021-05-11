import sys
import os
import sagemaker
from sagemaker import get_execution_role
import boto3 
import random
import datetime
import math
import time
import numpy as np
     
from concurrent import futures
     
num_thread = 8
throughput_interval = 10
throughput_time = 120
latency_window_size = 1000
batch_size = 1
live = True
num_infer = 0
latency_list = []
num_error = 0
def one_thread(endpoint_name, feed_data):
    global latency_list
    global num_infer
    global live
    global num_error
    sagemaker_session = sagemaker.Session()
     
    role = get_execution_role()
    pred = sagemaker.predictor.Predictor(endpoint_name)
    sm_runtime = boto3.Session().client('sagemaker-runtime')
    while True:
        start = time.time()
        try:
            #pred.predict(feed_data)
            sm_runtime.invoke_endpoint(EndpointName=endpoint_name, 
                                   ContentType='application/x-image',     
                                   Body=feed_data)
            #response = sm_runtime.invoke_endpoint(EndpointName=endpoint_name,ContentType='application/x-image',Body=feed_data)
            #if response['ResponseMetadata']['HTTPStatusCode'] != 200:
                #num_error += 1
        except:
            num_error += 1
        pass
            
     
        latency = time.time() - start
        latency_list.append(latency)
        num_infer += batch_size
        if not live:
            break
     
def current_performance():
    last_num_infer = num_infer
    print(' FPS  |  P50  |  P90  |  P95  |  P99  |  err  ')
     
    for _ in range(throughput_time // throughput_interval):
     
        current_num_infer = num_infer
        throughput = (current_num_infer - last_num_infer) / throughput_interval
        client_avg = 0.0
        client_p50 = 0.0
        client_p90 = 0.0
        client_p95 = 0.0
        client_p99 = 0.0
        if latency_list:
            client_avg = np.mean(latency_list[-latency_window_size:])
            client_p50 = np.percentile(latency_list[-latency_window_size:], 50)
            client_p90 = np.percentile(latency_list[-latency_window_size:], 90)
            client_p95 = np.percentile(latency_list[-latency_window_size:], 95)
            client_p99 = np.percentile(latency_list[-latency_window_size:], 99)
        print('{:5.3f}|{:.5f}|{:.5f}|{:.5f}|{:.5f} |{:4d}'.format(throughput, client_p50, client_p90, client_p95, client_p99, int(num_error) ))
        last_num_infer = current_num_infer
     
        time.sleep(throughput_interval)
    global live
    live = False
        
if __name__ == '__main__':
        
        num_thread = int(sys.argv[1]) # First cmd line argument: number of concurrent client threads (int)
        endpoint_name = sys.argv[2] # Second command line argument: SageMaker Endpoint Name (str)
        #num_thread = 10
        #endpoint_name = 'sagemaker-neo-pytorch-ml-inf1-2021-03-21-13-23-36-449'
        throughput_interval = 10
        throughput_time = 1200
        latency_window_size = 1000
        batch_size = 1
     
        with open('birds_lowres.jpg', 'rb') as f:
            payload = f.read()
     
     
        executor = futures.ThreadPoolExecutor(max_workers=num_thread+1)
        executor.submit(current_performance)
        for pred in range(num_thread):
            executor.submit(one_thread, endpoint_name, payload)