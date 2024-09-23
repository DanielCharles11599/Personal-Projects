from PIL import Image, ImageEnhance, ImageFilter
import os

path = "./imgs" # This variable must be the import folder
path_out = "./editedImgs" # This is the path where edited images will be placed



# Check if the directory exists
if not os.path.exists(path):
    try:
        # Create the directory
        os.makedirs(path)
        print(f"Directory {path} created successfully.")
    except:
        print(f"An error occurred while creating the directory: {path}")

else:
    pass

if not os.path.exists(path_out):
    try:
        # Create the directory
        os.makedirs(path_out)
        print(f"Directory {path_out} created successfully.")
    except:
        print(f"An error occurred while creating the directory: {path}")

else:
    pass


# Listing the files in the directory
for filename in os.listdir(path):
    img = Image.open(f"{path}/{filename}")

    # Enhancements are added here
    edit = img.filter(ImageFilter.SHARPEN).rotate(-90)

    factor = 1.5
    enhancer = ImageEnhance.Contrast(edit)
    edit = enhancer.enhance(factor)

    clean_name = filename + "_edited" #os.path.splitext(filename)[0]

    output_file_path = os.path.join(path_out, f"{clean_name}_edited.jpg")
    edit.save(output_file_path)
