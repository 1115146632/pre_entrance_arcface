#tmux kill-session -t pre_entrance_face
tmux new -d -s pre_entrance_face
tmux send -t pre_entrance_face "python3 manage.py runserver 0.0.0.0:8024"
#tmux attach-session -t pre_entrance_face
