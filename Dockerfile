# Demo de PolyRL en Cloud Run (EVA-09). La imagen lleva solo lo que la demo lee: la app, el paquete,
# las configuraciones, el tema y los reportes versionados. Sin dataset, modelos ni trayectorias
# completas: usa la muestra de test de app/trayectorias/. Se prueba en local con make demo-imagen.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080

# get_paths() resuelve configs/ y reports/ desde el directorio de trabajo.
WORKDIR /srv/polyrl

COPY app/requirements.txt app/requirements.txt
RUN pip install -r app/requirements.txt

COPY .streamlit .streamlit
COPY configs configs
COPY src src
COPY reports reports
COPY app app

RUN useradd --create-home polyrl
USER polyrl

EXPOSE 8080
# Cloud Run entrega el puerto en $PORT; exec deja a Streamlit como PID 1 para que reciba SIGTERM.
CMD ["sh", "-c", "exec streamlit run app/demo.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true"]
