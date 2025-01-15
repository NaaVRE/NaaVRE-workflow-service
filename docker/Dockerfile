FROM condaforge/mambaforge:24.9.0-0 AS build

RUN conda install -c conda-forge conda-pack
COPY environment.yaml .
COPY requirements.txt .

RUN mamba env update --name venv -f environment.yaml

RUN mamba clean --all -y

RUN conda-pack -n venv -o /tmp/env.tar && \
    mkdir /venv && cd /venv && tar xf /tmp/env.tar && \
    rm /tmp/env.tar
RUN /venv/bin/conda-unpack

FROM python:3.11-slim AS runtime

COPY --from=build /venv/ /venv/
ENV PATH=/venv/bin:$PATH
RUN chmod +x /venv/bin/activate
SHELL ["/bin/bash", "-c","/venv/bin/activate"]
RUN echo "source /venv/bin/activate" >> ~/.bashrc
SHELL ["/bin/bash", "--login", "-c"]

COPY requirements.txt .

# RUN pip install -r requirements.txt

WORKDIR /code

COPY ./app /code/app

CMD ["fastapi", "run", "app/main.py", "--port", "8000"]
