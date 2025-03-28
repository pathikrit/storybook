# Story Generator
A quick and dirty app to read aloud bedtime stories

![App](https://pbs.twimg.com/media/GnI3l47WAAA1bMB?format=jpg)

## Installation
```shell
git clone git@github.com:pathikrit/storybook.git
cd storybook
echo "OPENAI_API_KEY=???" >> .env
poetry env use 3.11
poetry install --no-root
```

## Run
```
poetry run streamlit run app.py
```
