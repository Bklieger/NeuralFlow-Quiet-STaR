"""
    NeuralFlow - Plot intermediate output of Mistral 7B

    Copyright (C) 2024 Lukas Valine

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import datetime
import os

import imageio
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image, ImageDraw, ImageFont
from transformers import MistralForCausalLM, AutoTokenizer, AutoConfig

device_0 = "cuda:0"
model_folder = "/notebooks/quietstar-8-ahead"
image_output_folder = "/notebooks/"

def main():
    config = AutoConfig.from_pretrained(model_folder)
    mistral = MistralForCausalLM.from_pretrained(
        model_folder,
        torch_dtype=torch.float16,
        device_map=device_0,
        use_flash_attention_2=False,
        config=config, )

    tokenizer = AutoTokenizer.from_pretrained(
        model_folder, trust_remote_code=True)

    # The last token of this string will be used to generate the image
    probe_string = "1 + 1 ="

    # Probe results is an array so that you can plot the changes to the
    # output over time. The plot_embedding_flow will generate an animated gif.
    # Call compute_model_output multiple times and append the results to
    # probe_results.
    probe_results = []
    generated_tokens = []
    top_tokens_list = []
    
    for _ in range(3):  # Generate 3 tokens sequentially as an example
        probe_result, top_tokens = compute_model_output(mistral, tokenizer, probe_string)
        probe_results.append(probe_result)
        top_tokens_list.append(top_tokens)
        print("Top tokens:", top_tokens)
        next_token = select_top_token(top_tokens)
        generated_tokens.append(next_token)
        probe_string += " " + next_token

    print("Generated tokens:", generated_tokens)
    
    plot_embedding_flow(probe_results, top_tokens_list)


def compute_model_output(base_model, tokenizer, ground_truth):
    with torch.no_grad():
        layer_output = []

        encoding = tokenizer(ground_truth, return_tensors="pt")
        input_ids = encoding['input_ids'].to(device_0)

        hidden_states = base_model.model.embed_tokens(input_ids)

        sequence_length = hidden_states.shape[1]
        batch_size = hidden_states.shape[0]
        position_ids = torch.arange(sequence_length, device=device_0).unsqueeze(0)
        position_ids = position_ids.expand(batch_size, -1)

        attention_mask = torch.triu(torch.full(
            (sequence_length, sequence_length), float('-inf')), diagonal=1)
        attention_mask = attention_mask.to(device_0)
        attention_mask = attention_mask.unsqueeze(0).unsqueeze(0)

        # Loop over layers
        for layer in base_model.model.layers:
            output = layer(hidden_states,
                           attention_mask=attention_mask,
                           position_ids=position_ids,
                           output_attentions=True)
            hidden_states = output[0]
            layer_output.append(hidden_states)

        logits = base_model.lm_head(hidden_states)
        softmax_logits = torch.softmax(logits, dim=-1)
        top_probabilities, top_indices = torch.topk(softmax_logits, 5, dim=-1)  # Get top 5 tokens

        top_tokens = [(tokenizer.decode(top_indices[0, -1, i]), top_probabilities[0, -1, i].item())
                      for i in range(5)]

        return layer_output, top_tokens


def select_top_token(top_tokens):
    # For simplicity, select the token with the highest probability
    top_tokens.sort(key=lambda x: x[1], reverse=True)
    return top_tokens[0][0]


def vectorized_get_color_rgb(value_tensor, max_value=1.0):
    h = (value_tensor * 1.0) / max_value
    s = torch.ones_like(h)
    v = torch.ones_like(h)

    c = v * s
    x = c * (1 - torch.abs((h * 6) % 2 - 1))
    m = v - c

    h1 = (h * 6).int()
    rgb = torch.stack((
        torch.where((h1 == 0) | (h1 == 5), c, torch.where((h1 == 1) | (h1 == 4), x, 0)),
        torch.where((h1 == 1) | (h1 == 2), c, torch.where((h1 == 0) | (h1 == 3), x, 0)),
        torch.where((h1 == 3) | (h1 == 4), c, torch.where((h1 == 2) | (h1 == 5), x, 0)),
    ), dim=-1) + m.unsqueeze(-1)

    return rgb


def generate_filename(prefix, extension):
    current_time = datetime.datetime.now()
    formatted_time = current_time.strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{formatted_time}.{extension}"
    return filename


def plot_layers(all_words, title, file_path, top_tokens_list, normalize=True):
    sequence_length = all_words[0].shape[1]
    paths = []

    all_words_cat = torch.cat(all_words, dim=0)
    global_min_val = torch.min(all_words_cat)
    global_max_val = torch.max(all_words_cat)

    global_mean = torch.mean(all_words_cat)
    global_var = torch.var(all_words_cat) * 25

    if normalize:
        min_val = global_mean - global_var
        max_val = global_mean + global_var
    else:
        min_val = global_min_val
        max_val = global_max_val

    for i in range(sequence_length):
        list_of_tensors = []
        for tensor in all_words:
            list_of_tensors.append(tensor[:, i, :])

        # Step 1: Concatenate tensors along width
        full_tensor = torch.cat(list_of_tensors, dim=0)  # Shape: [1, 4096 * 31]
        height = 512

        tensor_split = [F.pad(t, (0, max(0, height - t.shape[1])),
                              'constant', max_val.item()) for t in
                        torch.split(full_tensor, height, dim=1)]
        reshaped_tensor = torch.cat(tensor_split, dim=0)
        reshaped_tensor = torch.abs(reshaped_tensor)

        # Normalize data
        normalized_data = (reshaped_tensor - min_val) / (max_val - min_val)
        color_tensor = vectorized_get_color_rgb(normalized_data)

        # Generate image
        array = (color_tensor.cpu().numpy() * 255).astype(np.uint8)
        image = Image.fromarray(array, 'RGB')

        # Resize canvas to add space for text
        new_height = height + 60
        new_image = Image.new("RGB", (image.width, new_height), (0, 0, 0))
        new_image.paste(image, (0, 0))

        # Draw token text on the image
        draw = ImageDraw.Draw(new_image)
        try:
            font = ImageFont.truetype("arial.ttf", 14)
        except IOError:
            font = ImageFont.load_default()
        
        # Prepare the text with tokens and probabilities
        token_text = "\n".join([f"{repr(token)}: {prob:.5f}" for token, prob in top_tokens_list[i]])
        
        text_position = (10, height + 5)
        draw.text(text_position, token_text, fill="white", font=font)

        # Save the image
        tmp_name = "raw_values_tmp" + str(i)
        filename = title + "_" + generate_filename(tmp_name + str(i), "png")
        full_path = os.path.join(file_path, filename)
        new_image.save(full_path)

        paths.append(full_path)

    # Create gif from images
    filename = title + "_" + generate_filename("layers", "gif")
    gif_path = os.path.join(file_path, filename)
    with imageio.get_writer(gif_path, mode='I', fps=15, loop=0) as writer:
        for filename in paths:
            image = imageio.imread(filename)
            writer.append_data(image)

    # Remove temporary files
    for filename in paths:
        os.remove(filename)

    return gif_path


def plot_embedding_flow(probe_results, top_tokens_list):
    layer_count = len(probe_results[0])
    layer_embeddings = []
    for l_index in range(layer_count):
        sequence_embedding = []
        for probe_result in probe_results:
            embedding = probe_result[l_index][:, -1, :]
            sequence_embedding.append(embedding)
        layer_embedding = torch.stack(sequence_embedding, dim=1)
        layer_embeddings.append(layer_embedding)

    # Plot current progress
    path = plot_layers(layer_embeddings, "probe_results", image_output_folder, top_tokens_list)
    return path


if __name__ == "__main__":
    main()
