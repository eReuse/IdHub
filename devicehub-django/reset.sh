rm db/*
python3 manage.py migrate
python3 manage.py add_institution Pangea
python3 manage.py add_user Pangea user@example.org 1234 True
python3 manage.py up_snapshots example/snapshots/ user@example.org
