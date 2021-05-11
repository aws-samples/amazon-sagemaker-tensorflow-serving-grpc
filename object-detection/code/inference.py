print('******* in inference.py *******')
import tensorflow as tf
from tensorflow.keras.preprocessing import image
print(f'TensorFlow version is: {tf.version.VERSION}')

import io
import base64
import json
import numpy as np
from numpy import argmax
from collections import namedtuple
from PIL import Image
import time
import requests
import sys

# Imports for GRPC invoke on TFS
import grpc
from tensorflow.compat.v1 import make_tensor_proto
from tensorflow_serving.apis import predict_pb2
from tensorflow_serving.apis import prediction_service_pb2_grpc

import os
# default to use of GRPC
PREDICT_USING_GRPC = os.environ.get('PREDICT_USING_GRPC', 'true')
print('PREDICT_USING_GRPC')
print(PREDICT_USING_GRPC)
if PREDICT_USING_GRPC == 'true':
    USE_GRPC = True
else:
    USE_GRPC = False
    
MAX_GRPC_MESSAGE_LENGTH = 512 * 1024 * 1024

HEIGHT = 640
WIDTH  = 640

# Restrict memory growth on GPU's
physical_gpus = tf.config.experimental.list_physical_devices('GPU')
if physical_gpus:
  try:
    # Currently, memory growth needs to be the same across GPUs
    for gpu in physical_gpus:
        tf.config.experimental.set_memory_growth(gpu, True)
    logical_gpus = tf.config.experimental.list_logical_devices('GPU')
    print(len(physical_gpus), 'Physical GPUs,', len(logical_gpus), 'Logical GPUs')
  except RuntimeError as e:
    # Memory growth must be set before GPUs have been initialized
    print(e)
else:
    print('**** NO physical GPUs')


num_inferences = 0
print(f'num_inferences: {num_inferences}')

Context = namedtuple('Context',
                     'model_name, model_version, method, rest_uri, grpc_uri, '
                     'custom_attributes, request_content_type, accept_header')

def handler(data, context):

    global num_inferences
    num_inferences += 1
    
    print(f'\n************ inference #: {num_inferences}')
    if context.request_content_type == 'application/x-image':
        stream = io.BytesIO(data.read())
        img = Image.open(stream).convert('RGB')
        img = img.resize((WIDTH, HEIGHT))
        img_array = image.img_to_array(img)
        img_array = img_array.reshape((HEIGHT, WIDTH, 3)).astype(np.uint8) #"channels_last"
        x = np.expand_dims(img_array, axis=0)
        instance = x #no additional preprocessing
        print(f'    final image shape: {instance.shape}')
        print(f'    final image size: {instance.nbytes}')
        del x, img
    else:
        _return_error(415, 'Unsupported content type "{}"'.format(context.request_content_type or 'Unknown'))

    start_time = time.time()
    
    if USE_GRPC:
        prediction = _predict_using_grpc(context, instance)

    else: # use TFS REST API
        inst_json = json.dumps({'instances': instance.tolist()})
        print('rest call')
        response = requests.post(context.rest_uri, data=inst_json)
        if response.status_code != 200:
            raise Exception(response.content.decode('utf-8'))
        res = response.content
        request_size = sys.getsizeof(inst_json)
        response_size = sys.getsizeof(res)
        print('request payload size')
        print(request_size)
        print('response payload size')
        print(response_size)
        #below postprocessing slows down inference further so we will leave it to be done at client side
        #prediction_json = {'detection_boxes': json.loads(res)['predictions'][0]['detection_boxes']}
        #prediction = json.dumps(prediction_json)
        prediction = res
    end_time   = time.time()
    latency    = int((end_time - start_time) * 1000)
    print(f'=== TFS invoke took: {latency} ms')
    
    print('complete')
    print(context.accept_header)
    response_content_type = context.accept_header
    return prediction, response_content_type

def _return_error(code, message):
    raise ValueError('Error: {}, {}'.format(str(code), message))

def _predict_using_grpc(context, instance):
    print(instance)
    request = predict_pb2.PredictRequest()
    request.model_spec.name = 'model'
    request.model_spec.signature_name = 'serving_default'

    request.inputs['input_tensor'].CopyFrom(make_tensor_proto(instance))
    options = [
        ('grpc.max_send_message_length', MAX_GRPC_MESSAGE_LENGTH),
        ('grpc.max_receive_message_length', MAX_GRPC_MESSAGE_LENGTH)
    ]
    channel = grpc.insecure_channel(f'0.0.0.0:{context.grpc_port}', options=options)
    stub = prediction_service_pb2_grpc.PredictionServiceStub(channel)
    result_future = stub.Predict.future(request, 60)  # 5*2 seconds  
    output_tensor_proto = result_future.result().outputs['detection_boxes']
    
    output_shape = [dim.size for dim in output_tensor_proto.tensor_shape.dim]
    
    
    output_np = np.array(output_tensor_proto.float_val).reshape(output_shape)
    prediction_json = {'detection_boxes': output_np.tolist()}
    return json.dumps(prediction_json)
    
def _print_image_metadata(img):
    # Retrieve the attributes of the image
    fileFormat      = img.format       
    imageMode       = img.mode        
    imageSize       = img.size  # (width, height)
    colorPalette    = img.palette       

    print(f'    File format: {fileFormat}')
    print(f'    Image mode:  {imageMode}')
    print(f'    Image size:  {imageSize}')
    print(f'    Color pal:   {colorPalette}')

    print(f'    Keys from image.info dictionary:')
    for key, value in img.info.items():
        print(f'      {key}')