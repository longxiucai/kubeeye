# pip install -r requirements.txt
# export PYTHONPATH=/home/lyx/desktop/feature/kubeeye/kubeeye
# export KUBEEYE_DATA_DIR=/home/lyx/desktop/feature/kubeeye/data
# streamlit run app.py --server.port=8501 --server.address=0.0.0.0




# docker run -d \
#   --name kubeeye \
#   -p 8501:8501 -p 8000:8000 \
#   -v /file/code/kubeeye-lyx-git/kubeeye/data:/app/data \
#   -v $PWD/supervisord.conf:/etc/supervisord.conf \
#   -v /etc/localtime:/etc/localtime:ro \
#   kubeeye:1

supervisord -c supervisord.conf