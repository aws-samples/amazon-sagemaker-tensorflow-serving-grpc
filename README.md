## Reduce computer vision inference latency using gRPC with TensorFlow serving on Amazon SageMaker

REST APIs to serve models with large payload like images can cause high latency in ML applications. In-server communucation with TensorFlow serving on Amazon SageMaker uses REST by default. Customers are free to update this to use high performant gRPC communication instead. However, there is a lack of step by step guidance and benchmark performance benefits.

In this post, we demonstrate how to use gRPC for in-server communication between SageMaker and TensorFlow serving. We show two computer vision examples using pre-trained models, one for image classification and the other for object detection. We compare and contrast the inference script with SageMaker TensorFlow serving for REST and gRPC, and provide latency benchmarks for each of them. 

Customers who have performance concerns can use this solution as a reference while deploying TensorFlow models with large payloads on Amazon SageMaker.

We use a pre-trained MobileNet Keras application for image classification and a pre-trained EfficientDet TF2 model for object detection. We deploy both on Amazon SageMaker with an inference script that implements a handler function to perform preprocessing and inference with TensorFlow serving. We create one endpoint with REST in-server communication with TFS and another using gRPC. We demonstrate latency for each of these endpoints for each use case with a sample image.  

![image (5)](https://user-images.githubusercontent.com/8871432/118111158-37c81000-b3db-11eb-8ab2-45b04366e64b.png)


## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

