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
poetry run fastapi dev server.py
```
