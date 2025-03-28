
# Framework

![framework](framework.png)

# Usage

## Dataset

```python
ESFAN/

|_ datasets
|     |_ BCSS-WSSS/
|         |_ train/img/
|         |_ val/img/
|          |     |/mask/
|         |_ test/img/
|          |     |/mask/
|     |_ LUAD-HistoSeg/
|         |_ train/img/
|         |_ val/img/
|          |     |/mask/
|         |_ test/img/
|          |     |/mask/
```

## Pretrained weights and datasets

Download the pretained weight of classification stage via Google Cloud Drive ([Link)](https://drive.google.com/file/d/1Rka2SzqAwxUEFb28tbmiy2anhkkFOnTg/view?usp=drive_link)

Download the datasets via Google Cloud Drive ([Link)](https://drive.google.com/file/d/1lWAeCp6UN30VRVmqv97kA2sJ1Pp2frhC/view?usp=drive_link)([Link)](https://drive.google.com/file/d/178eSM9xs5jITt5P2kjaswDlJzwlU5gps/view?usp=drive_link)
## Run each step:

1、Train the classification model and generate pesudo masks with the image-level label:

```python
python 1_train_stage1.py
```

2、Train the segmentation model with pesudo masks:

```python
python 2_train_stage2.py
```

3、Inference with the weights obtained from the segmentation stage：

```python
python inference.py
```

