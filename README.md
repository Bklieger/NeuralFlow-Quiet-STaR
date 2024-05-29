# Neural Flow

This is a Python script for plotting the intermediate layer outputs of Mistral 7B. When you run the script, it produces a 512x256 image representing the output at every layer of the model.

The concept is straightforward: collect the output tensors from each layer, normalize them between zero and one, and plot these values as a heatmap. The resulting image reveals a surprising amount of structure. I have found this enormously helpful for visually inspecting outputs when fine-tuning models.

### Visualizing the model during training

Below is a visualization from an out-of-the-box, non-fine-tuned Mistral 7B.

![initial_output](https://github.com/valine/NeuralFlow/assets/14074844/aef6a0fc-820c-4e6d-94df-a907df8a7018)


Intentionally overfitting a model on a small fine-tuning dataset yields the following output. A problem starts around layer 10, cascading through the subsequent layers.

![overfit_output](https://github.com/valine/NeuralFlow/assets/14074844/c6788265-5c8c-45ba-8092-98ec6d3caf09)

The true value of this visualization lies in the patterns that emerge when comparing outputs before and after training. By periodically visualizing the model output, it's possible to animate the model's intermediate output over time. Failures within a single layer can cascade to higher layers. While it's challenging to ascribe meaning to the structures within the visualization, it's visually apparent when the distribution of output deviates from the initial state.

https://github.com/valine/NeuralFlow/assets/14074844/1f2e50ea-d64d-4f37-a991-f968399e29bd

### How the image is structured

The resolution and structure of this visualization warrant additional explanation. The intermediate output of Mistral 7B for a single token is a 4096-dimension tensor for each of the 32 layers. A 4096x32 image is impractical for visualization purposes. To address this, I have segmented the image into chunks of 512 and arranged them vertically. The result is a 512x256 image that displays nicely on landscape screens.


![guide](https://github.com/valine/NeuralFlow/assets/14074844/7cf5ad4a-98a7-4ec4-896c-fe4fb5068654)

### Additional discusion and models
This tool was developed as part of an independent research project. Per the request of a few users of r/locallama the code has been cleaned up and made avaiable in this repo. You can find that original discussion here:
[thread on r/locallama](https://www.reddit.com/r/LocalLLaMA/comments/1ap8mxh/comment/kq4mdk4/?context=3)

As a final note, here are a few models I have trained using this visualization as a guide. In my opinion the behaviors these models were trained on generalized exceptionally well. 
- https://huggingface.co/valine/OpenPirate
- https://huggingface.co/valine/MoreHuman
- https://huggingface.co/valine/OpenAusten
- https://huggingface.co/valine/OpenSnark
- https://huggingface.co/valine/OpenDracula

# Constants
There are two file paths you will want to change before running the script:

```
model_folder = "/models/OpenHermes-2.5-Mistral-7B"
image_output_folder = "/home/username/Desktop/"
```
# Updates
Top tokens are printed after each generation:

probe_string = "1 + 1="

First token generation: [('', 0.0003376007080078125), ('<|startthought|>', 0.00022661685943603516), ('\n', 0.00021028518676757812), ('?', 0.0001747608184814453), ('a', 0.00015783309936523438)]

Second token generation: [('2', 0.0006198883056640625), ('3', 0.0005059242248535156), ('1', 0.0004715919494628906), ('4', 0.00037670135498046875), ('0', 0.0003402233123779297)]

Third token generation: [('\n', 0.0003523826599121094), ('.', 0.0002887248992919922), (',', 0.0002868175506591797), ('<|startthought|>', 0.000263214111328125), ('', 0.0002465248107910156)]

Generated tokens: ['', '2', '\n']

# To-do

Add token output as overlay under each image frame

This is self explanitory, but set the model folder to the location of your Mistral 7B, and the image output folder to the path you'd like to save your image.
