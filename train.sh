# DATADIR="/deep/group/med/mimic-iii/train/"
# DATADIR="/Users/dmorina/mnt/cdr_mimic/"
DATADIR="/deep/group/sharonz/cdr_mimic/data"
NAME="DEBUG_DATA_SPLIT"
NUM_EPOCHS=1000
MODEL="SimpleNN"
LR=1e-6

ARGUMENTS="--data_dir $DATADIR --name $NAME --num_epochs $NUM_EPOCHS --model $MODEL --lr $LR --verbose"

python train.py ${ARGUMENTS}