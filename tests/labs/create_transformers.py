#!/usr/bin/env python3

import torch
import transformers

from transformers import GPT2LMHeadModel, GPT2Tokenizer

class TransformersModel():
    def __init__(self, model=None, class_name=None, model_type=None):
        self.model = model
        self.automodel_class_name = class_name
        self.model_type = model_type


    def save_torch_safetensors(self, model_fpath):
        try:
            self.model.save_pretrained(f'{model_fpath}', safe_serialization=True)
        except Exception as e:
            print(f'Torch safetensors save error: {e}')


    def save_torch_weights(self, model_fpath, with_arch=True):
        try:
            params = { 'model_state_dict': self.model.state_dict() }
            if with_arch:
                params['model_architecture'] = self.model
            torch.save(params, f'{model_fpath}.pth')
        except Exception as e:
            print(f'Torch weights save error: {e}')


    def save_torch_script(self, model_fpath):
        try:
            torch.jit.script(self.model).save(f'{model_fpath}.torchscript.pt')
        except Exception as e:
            print(f'Torch script save error: {e}')

    
    def save_torch_onnx(self, model_fpath):
        try:
            model = GPT2LMHeadModel.from_pretrained('gpt2')
            tokenizer = GPT2Tokenizer.from_pretrained('gpt2')
            dummy_text = "Hello, this is a test"
            inputs = tokenizer(dummy_text, return_tensors="pt")
            input_ids = inputs["input_ids"]
            model.config.use_cache = False
            torch.onnx.export(
                model,
                input_ids,
                f"{model_fpath}.onnx",
                input_names=["input_ids"],
                output_names=["logits"],
                dynamic_axes={
                    "input_ids": {0: "batch_size", 1: "sequence_length"},
                    "logits": {0: "batch_size", 1: "sequence_length"}
                },
                opset_version=14
            )
        except Exception as e:
            print(f'Torch script save error: {e}')


    def save_traced(self, model_fpath):
        try:
            example_input_ids = torch.randint(0, 50257, (1, 8))
            example_attention_mask = torch.ones(1, 8, dtype=torch.long)
            traced = torch.jit.trace(self.model, (example_input_ids, example_attention_mask))
            traced.save(f'{model_fpath}.traced.pt')
        except Exception as e:
            print(f'Torch traced save error: {e}')


class TransformersModelFactory():
    def __init__(self):
        self.auto_model_combos = {}
        self.get_auto_model_combos()


    def get_auto_model_combos(self):
        for automodel_class_name in dir(transformers):
            if not automodel_class_name.startswith('AutoModel'):
                continue
            automodel_class = getattr(transformers, automodel_class_name)

            for automodel_cfg in automodel_class._model_mapping:

                try:
                    type_name = automodel_cfg.model_type
                    cfg_name = automodel_cfg.__name__
                    arch_name = automodel_class._model_mapping[automodel_cfg].__name__
                except AttributeError:
                    continue
                except:
                    breakpoint()

                if automodel_class_name not in self.auto_model_combos:
                    self.auto_model_combos[automodel_class_name] = {}
                if type_name not in self.auto_model_combos[automodel_class_name]:
                    self.auto_model_combos[automodel_class_name][type_name] = {}
                self.auto_model_combos[automodel_class_name][type_name]['config'] = cfg_name
                self.auto_model_combos[automodel_class_name][type_name]['arch'] = arch_name


    def reconstruct_model(self, automodel_class_name, model_type):
        tmodel = None
        automodel_class = getattr(transformers, automodel_class_name)
        try:
            cfg = transformers.AutoConfig.for_model(model_type=model_type)
            model = automodel_class.from_config(cfg)
            model.eval() # We don't train here.
            tmodel = TransformersModel(model, automodel_class_name, model_type)
            
        except Exception as e:
            print(f'Build error: {e}')

        return tmodel


    


factory = TransformersModelFactory()
gpt2 = factory.auto_model_combos['AutoModelForCausalLM']['gpt2']

tmodel = factory.reconstruct_model('AutoModelForCausalLM', 'gpt2')
#tmodel.save_torch_safetensors('./output/gpt2-safetensors')
#tmodel.save_torch_weights('./output/gpt2-weights')
#BROKEN tmodel.save_traced('./output/gpt2-traced')
tmodel.save_torch_onnx('./output/gpt2onnx')

breakpoint()