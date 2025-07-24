#!usr/bin/bash
clear

python3 case_study.py --experiment 1
python3 case_study.py --experiment 2
python3 case_study.py --experiment 3
python3 case_study.py --experiment 4

sh plot.sh
