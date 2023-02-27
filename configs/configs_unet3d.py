import albumentations as A

from cv2 import BORDER_CONSTANT,INTER_CUBIC,INTER_LINEAR
from math import ceil

MONTHS = ['03','04','08','10','11','12']
ADDITIONAL_INPUTS = None
INCLUDE_NIR = True

epochs = 300
learning_rate = 0.001
fold = 3

version = 21
batch_size = 4

RESIZE = 256
PAD = True
PADSIZE = 352
if PAD and PADSIZE is None:
    if RESIZE is None:
        PADSIZE = 256 + 32
    else:
        RESIZE = max(256,int(ceil(RESIZE/32)*32))
        PADSIZE = RESIZE + 32


IN_CHANNELS = 3 + int(INCLUDE_NIR)
if ADDITIONAL_INPUTS is not None:
    IN_CHANNELS += len(ADDITIONAL_INPUTS)

additional_targets={f'image_{m}':'image' for m in MONTHS}

test_transform = A.Compose(
    [   
        A.Resize(height=RESIZE,width=RESIZE,interpolation=INTER_CUBIC,p=1.0) if RESIZE is not None else A.NoOp(),
        A.PadIfNeeded(min_height=PADSIZE,min_width=PADSIZE,border_mode=BORDER_CONSTANT,value=[-1]*4,mask_value=-100,p=1)\
             if PAD else A.NoOp(),
        
    ],
    p=1.0,
    additional_targets=additional_targets
)
transform = A.Compose(
    [
        A.Resize(height=RESIZE,width=RESIZE,interpolation=INTER_CUBIC,p=1.0) if RESIZE is not None else A.NoOp(),

        #Flips and rotations
        A.VerticalFlip(p=0.5),
        A.HorizontalFlip(p=0.5),
        A.RandomRotate90(p=0.5),

        #Color AUgs
        #A.RandomBrightnessContrast(contrast_limit=(-0.02,0.02),brightness_limit=0,brightness_by_max=True,p=0.3),

        test_transform,

        #A.ShiftScaleRotate(
        #    shift_limit=0.0,scale_limit=0.0,rotate_limit=(-30,30),
        #    border_mode=BORDER_CONSTANT,value=[-1]*4,mask_value=0.0,p=0.5),

        
    ],
    p=1.0,
    additional_targets=additional_targets
)
#transform = None

#UTAE
backbone = 'tu-repvgg_b0'
backbone = 'tu-tf_efficientnetv2_s'
#backbone = 'tu-resnet50'
#skresnet34
model_name = 'UNET3D'
cfg = {
    
    'train_tfm': A.to_dict(transform) if transform is not None else None,
    'test_tfm' : A.to_dict(test_transform) if test_transform is not None else None,
    
    'resize' : RESIZE,
    'pad' : PAD,
    'padsize' : PADSIZE,
    
    'model_name' : model_name,
    'random_rotate' : {
        'apply' : True,
        'proba' : 0.5,
        'angle' : 30
    },

    'random_mask_ignore' : {
        'apply' : True,
        'proba' : 0.8,
        'min_width' : 80,
        'max_width' : 150
    },
    'mask_pixel_drop' : {
        'apply' : False,
        'neg_drop' : (30,50),
        'pos_drop' : (30,50)
    },
    'model' : dict(
        tsteps = len(MONTHS),
        conv3d_mode = 'conv3d_pc',
        kernel_3d = 3,
        dropout = 0.5,
        ch_mul = 4,
        group_norm = True,
        group_norm_channels=4,
        replace_all_norms=False,
        sa_att = True,
        use_relu=True,
        use_aspp = False,
        sep_aspp = True,
        dense_aspp=False,
        atrous_rates=(6,12,18),
        encoder_name = backbone,
        encoder_depth = 5,
        encoder_weights = True,
        decoder_use_batchnorm = True,
        decoder_channels = (256,128, 64, 64, 32),
        decoder_attention_type= None,
        in_channels = IN_CHANNELS,
        classes = 1,
        activation = None,
        aux_params = None,
        narrow_kernel_last=True,
        coord_conv = False,
        coord_conv_max_L = RESIZE if RESIZE is not None else 256
    ),

    'optimizer':
        {
            "name": "Adam",
            "kwargs": {
                "lr": learning_rate,
                "betas": [
                0.9,
                0.99
                ],
                "eps": 1e-08,
                "weight_decay": 0.0001,
                "amsgrad": False
            }
        },
    'scheduler':
        {
            'name' : 'polylrwwp',
            'kwargs':{
                'warmup' : 0,
                'epochs' : epochs,
                'ratio' : 0.9,
            }
        },

    'loss' : dict(
        alpha = 1.0,
        beta=1.0,
        gamma=0.0,
        pos_weight=1.0,
        dice_fn_w = 0.5,
        use_focal = True,
        bce_per_img = False,

        use_chole = 0,
        chole_weight = 0.5


    )
    ,

    'dataset': dict(

        root = '/home/hasann/Desktop/geogroup/competition_datasets/nasa_rwanda_field_boundary_competition',
        folds_path = '/home/hasann/Desktop/geogroup/competitions/nasa_rwanda_field_boundary_competition/folds.csv',
        fold = fold,
        months = MONTHS,
        #aug_tfm = A.to_dict(transform) if transform is not None else None,
        resize=None,
        smooth_mask = False,
        include_nir = INCLUDE_NIR 
        #additional_channels=ADDITIONAL_INPUTS
        #train = True
    )
        ,
    'training':
        {   'activation' : 'sigmoid',
            'epochs' : epochs,
            'lr' : learning_rate,
            'batch_size' : batch_size,
            'val_batch_size' : 1,
            'accumulation_steps':1,
            'val_freq' : 5,
            'device' : 'cuda',
            'amp' : False,
            'max_grad_norm' : 3.0,
            'use_mixup':True,
            'double_mixup' : True
        },


    'save_dir' : f'./results_folds_new/nasa_rfb_{model_name}_{backbone}_{epochs}epochs_fold{fold}_V{version}',



}

"""
A.OneOf([
            A.Affine(
                scale=1.2, translate_percent=(0,0.02), translate_px=None, 
                rotate=0.0, shear=(0,20.0),cval=[-1]*4, cval_mask=0, mode=BORDER_CONSTANT, fit_output=False, p=1.0),
            A.Affine(
                scale=1.1, translate_percent=(0,0.05), translate_px=None, 
                rotate=0.0, shear=(0,10.0),cval=[-1]*4, cval_mask=0, mode=BORDER_CONSTANT, fit_output=False, p=1.0),
            A.Affine(
                scale=(0.9,1.05), translate_percent=(0,0.08), translate_px=None, 
                rotate=0.0, shear=(0,10.0),cval=[-1]*4, cval_mask=0, mode=BORDER_CONSTANT, fit_output=False, p=1.0),
            A.ElasticTransform(
            alpha=1, sigma=10, alpha_affine=20, interpolation=1, 
            border_mode=BORDER_CONSTANT, value=[-1]*4, mask_value=0, 
            always_apply=False, approximate=False, same_dxdy=False, p=1.0)
        ],p=0.4)
"""