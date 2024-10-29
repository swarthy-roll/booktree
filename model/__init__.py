# importing all the models here makes them available to the database logic
import os, importlib

# dynamically import all model modules from the 'models' folder
# get current directory
model_dir = os.path.dirname(__file__)  

# import each model
for filename in os.listdir(model_dir):
    if filename.endswith('.py') and filename != '__init__.py':
        module_name = f'model.{filename[:-3]}'  # Strip off the '.py' to get module name
        importlib.import_module(module_name)
