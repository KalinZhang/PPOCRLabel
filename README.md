English | [简体中文](README_ch.md)

# PPOCRLabelv2

## 0. Quick Start

### Windows

Double click `startpwsh.bat` to start a terminal, and paste the following commands:

```pwsh
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force; .\setup.ps1
```

### MacOS

TODO


## 1. Installation and Run

### 1.1 Install PaddlePaddle

```bash
pip3 install --upgrade pip

# If you only have cpu on your machine, please run the following command to install
python3 -m pip install paddlepaddle
```


### 1.2 Install and Run PPOCRLabel



```bash
cd ./PPOCRLabel  # Switch to the PPOCRLabel directory

python PPOCRLabel.py 
```

## 2. Usage

### 2.1 Steps

1. Build and launch using the instructions above.

2. Click 'Open Dir' in Menu/File to select the folder of the picture.<sup>[1]</sup>

3. Click 'Auto recognition', use PP-OCR model to automatically annotate images which marked with 'X' <sup>[2]</sup>before the file name.

4. Create Box:

   4.1 Click 'Create RectBox' or press 'W' in English keyboard mode to draw a new rectangle detection box. Click and release left mouse to select a region to annotate the text area.

   4.2 Press 'Q' to enter four-point labeling mode which enables you to create any four-point shape by clicking four points with the left mouse button in succession and DOUBLE CLICK the left mouse as the signal of labeling completion.

5. After the marking frame is drawn, the user clicks "OK", and the detection frame will be pre-assigned a "TEMPORARY" label.

6. Click 're-Recognition', model will rewrite ALL recognition results in ALL detection box<sup>[3]</sup>.

7. Single click the result in 'recognition result' list to manually change inaccurate recognition results.

8. **Click "Check", the image status will switch to "√",then the program automatically jump to the next.**

9. Click "Delete Image", and the image will be deleted to the recycle bin.

10. Labeling result: the user can export the label result manually through the menu "File - Export Label", while the program will also export automatically if "File - Auto export Label Mode" is selected. The manually checked label will be stored in *Label.txt* under the opened picture folder. Click "File"-"Export Recognition Results" in the menu bar, the recognition training data of such pictures will be saved in the *crop_img* folder, and the recognition label will be saved in *rec_gt.txt*<sup>[4]</sup>.

11. Additional Feature Description
    - `File` -> `Re-recognition`: After checking, the newly annotated box content will automatically trigger the `Re-recognition` function of the current annotation box, eliminating the need to click the Re-identify button. This is suitable for scenarios where you do not want to use Automatic Annotation but prefer manual annotation, such as license plate recognition. In a single image with only one license plate, using Automatic Annotation would require deleting many additional recognized text boxes, which is less efficient than directly re-annotating.
    - `File` -> `Auto Save Unsaved changes`: By default, you need to press the `Check` button to complete the marking confirmation for the current box, which can be cumbersome. After checking, when switching to the next image (by pressing the shortcut key `D`), a prompt box asking to confirm whether to save unconfirmed markings will no longer appear. The current markings will be automatically saved and the next image will be switched, making it convenient for quick marking.
    - After selecting the bounding box, there are 5 shortcut keys available to individually control the movement of the four vertices of the bounding box, suitable for scenarios that require precise control over the positions of the bounding box vertices:
      - `z`: After pressing, the up, down, left, and right arrow keys will move the 1st vertex individually.
      - `x`: After pressing, the up, down, left, and right arrow keys will move the 2nd vertex individually.
      - `c`: After pressing, the up, down, left, and right arrow keys will move the 3rd vertex individually.
      - `v`: After pressing, the up, down, left, and right arrow keys will move the 4th vertex individually.
      - `b`: After pressing, the up, down, left, and right arrow keys will revert to the default action of moving the entire bounding box.

### 2.2 Table Annotation

The table annotation is aimed at extracting the structure of the table in a picture and converting it to Excel format,
so the annotation needs to be done simultaneously with external software to edit Excel.
In PPOCRLabel, complete the text information labeling (text and position), complete the table structure information
labeling in the Excel file, the recommended steps are:

1. Table annotation: After opening the table picture, click on the `Table Recognition` button in the upper right corner of PPOCRLabel, which will call the table recognition model in PP-Structure to automatically label
    the table and pop up Excel at the same time.

2. Change the recognition result: **label each cell** (i.e. the text in a cell is marked as a box). Right click on the box and click on `Cell Re-recognition`.
   You can use the model to automatically recognise the text within a cell.

3. Mark the table structure: for each cell contains the text, **mark as any identifier (such as `1`) in Excel**, to ensure that the merged cell structure is same as the original picture.

    > Note: If there are blank cells in the table, you also need to mark them with a bounding box so that the total number of cells is the same as in the image.

4. ***Adjust cell order:*** Click on the menu  `View` - `Show Box Number` to show the box ordinal numbers, and drag all the results under the 'Recognition Results' column on the right side of the software interface to make the box numbers are arranged from left to right, top to bottom

5. Export JSON format annotation: close all Excel files corresponding to table images, click `File`-`Export Table Label` to obtain `gt.txt` annotation results.

### 2.3 Note

[1] PPOCRLabel uses the opened folder as the project. After opening the image folder, the picture will not be displayed in the dialog. Instead, the pictures under the folder will be directly imported into the program after clicking "Open Dir".

[2] The image status indicates whether the user has saved the image manually. If it has not been saved manually it is "X", otherwise it is "√", PPOCRLabel will not relabel pictures with a status of "√".

[3] After clicking "Re-recognize", the model will overwrite ALL recognition results in the picture. Therefore, if the recognition result has been manually changed before, it may change after re-recognition.

[4] The files produced by PPOCRLabel can be found under the opened picture folder including the following, please do not manually change the contents, otherwise it will cause the program to be abnormal.

|   File name   |                         Description                          |
| :-----------: | :----------------------------------------------------------: |
|   Label.txt   | The detection label file can be directly used for PP-OCR detection model training. After the user saves 5 label results, the file will be automatically exported. It will also be written when the user closes the application or changes the file folder. |
| fileState.txt | The picture status file save the image in the current folder that has been manually confirmed by the user. |
|  Cache.cach   |    Cache files to save the results of model recognition.     |
|  rec_gt.txt   | The recognition label file, which can be directly used for PP-OCR identification model training, is generated after the user clicks on the menu bar "File"-"Export recognition result". |
|   crop_img    | The recognition data, generated at the same time with *rec_gt.txt* |



## 3. Explanation

### 3.1 Shortcut keys

| Shortcut keys            | Description                                      |
|--------------------------|--------------------------------------------------|
| Ctrl + Shift + R         | Re-recognize all the labels of the current image |
| W                        | Create a rect box                                |
| Q  or  Home              | Create a multi-points box                         |
| Ctrl + E                 | Edit label of the selected box                   |
| Ctrl + X                 | Change key class of the box when enable `--kie`  |
| Ctrl + R                 | Re-recognize the selected box                    |
| Ctrl + C                 | Copy and paste the selected box                  |
| Ctrl + Left Mouse Button | Multi select the label box                       |
| Backspace or Delete      | Delete the selected box                          |
| Ctrl + V  or End         | Check image                                      |
| Ctrl + Shift + d         | Delete image                                     |
| D                        | Next image                                       |
| A                        | Previous image                                   |
| Ctrl++                   | Zoom in                                          |
| Ctrl--                   | Zoom out                                         |
| ↑→↓←                     | Move selected box                                |
| Z, X, C, V, B     | Move the four vertices of the selected bounding box individually|

### 3.2 Built-in Model

- Default model: PPOCRLabel uses the Chinese and English ultra-lightweight OCR model in PaddleOCR by default, supports Chinese, English and number recognition, and multiple language detection.

- Model language switching: Changing the built-in model language is supportable by clicking "PaddleOCR"-"Choose OCR Model" in the menu bar. Currently supported languages​include French, German, Korean, and Japanese.
  For specific model download links, please refer to [PaddleOCR Model List](https://github.com/PaddlePaddle/PaddleOCR/blob/release/2.6/doc/doc_en/models_list_en.md)

- **Custom Model**: If users want to replace the built-in model with their own inference model, they can follow the [Custom Model Code Usage](https://github.com/PaddlePaddle/PaddleOCR/blob/release/2.6/doc/doc_en/whl_en.md#31-use-by-code) by modifying PPOCRLabel.py for [Instantiation of PaddleOCR class](https://github.com/PaddlePaddle/PaddleOCR/blob/release/2.6/PPOCRLabel/PPOCRLabel.py#L97) :

  add parameter `det_model_dir`  in `self.ocr = PaddleOCR(use_pdserving=False, use_angle_cls=True, det=True, cls=True, use_gpu=gpu, lang=lang) `

### 3.3 Export Label Result

PPOCRLabel supports three ways to export Label.txt

- Automatically export: After selecting "File - Auto Export Label Mode", the program will automatically write the annotations into Label.txt every time the user confirms an image. If this option is not turned on, it will be automatically exported after detecting that the user has manually checked 5 images.

  > The automatically export mode is turned off by default

- Manual export: Click "File-Export Marking Results" to manually export the label.

- Close application export

### 3.4 Dataset division

- Enter the following command in the terminal to execute the dataset division script:

    ```
  cd ./PPOCRLabel # Change the directory to the PPOCRLabel folder
  python gen_ocr_train_val_test.py --trainValTestRatio 6:2:2 --datasetRootPath ../train_data
  ```

  Parameter Description:

  - `trainValTestRatio` is the division ratio of the number of images in the training set, validation set, and test set, set according to your actual situation, the default is `6:2:2`

  - `datasetRootPath` is the storage path of the complete dataset labeled by PPOCRLabel. The default path is `PaddleOCR/train_data` .
  ```
  |-train_data
    |-crop_img
      |- word_001_crop_0.png
      |- word_002_crop_0.jpg
      |- word_003_crop_0.jpg
      | ...
    | Label.txt
    | rec_gt.txt
    |- word_001.png
    |- word_002.jpg
    |- word_003.jpg
    | ...
  ```

### 3.5 Error message

- If paddleocr is installed with whl, it has a higher priority than calling PaddleOCR class with paddleocr.py, which may cause an exception if whl package is not updated.

- For Linux users, if you get an error starting with **objc[XXXXX]** when opening the software, it proves that your opencv version is too high. It is recommended to install version 4.2:

    ```
    pip install opencv-python==4.2.0.32
    ```
- If you get an error starting with **Missing string id **,you need to recompile resources:
    ```
    pyrcc5 -o libs/resources.py resources.qrc
    ```
- If you get an error ``` module 'cv2' has no attribute 'INTER_NEAREST'```, you need to delete all opencv related packages first, and then reinstall the 4.2.0.32  version of headless opencv
    ```
    pip install opencv-contrib-python-headless==4.2.0.32
    ```

### 4. Related

1.[Tzutalin. LabelImg. Git code (2015)](https://github.com/tzutalin/labelImg)
