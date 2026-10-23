# BmC (the cubing engine) commit that goes into the image. To ship a newer
# engine, change this value and nothing else.
ARG BMC_REF=229600ea973a721c620a78799ed8ba8680a79caf

FROM scratch AS bmc
ARG BMC_REF
ADD https://github.com/Biodiversity-Meets-Data/BmC.git#${BMC_REF} /


FROM mambaorg/micromamba:2.9.0-debian12-slim
ARG BMC_REF
LABEL bmc.commit=${BMC_REF}

# The geospatial stack (GDAL, rasterio, ...) comes from conda-forge, as
# specified by BmC itself. This layer only changes when BMC_REF does.
COPY --from=bmc --chown=$MAMBA_USER:$MAMBA_USER /environment.yml /tmp/environment.yml
RUN micromamba install -y -n base -f /tmp/environment.yml \
    && micromamba clean --all --yes

# Writable locations for the unprivileged user.
USER root
RUN mkdir /app /output /tmp/bmc \
    && chown $MAMBA_USER:$MAMBA_USER /app /output /tmp/bmc
USER $MAMBA_USER
WORKDIR /app

# The engine. Its dependencies are in environment.yml, hence --no-deps.
# Only src/bmc is copied: the repository also tracks a stale src/bmc.egg-info.
ARG MAMBA_DOCKERFILE_ACTIVATE=1
COPY --from=bmc --chown=$MAMBA_USER:$MAMBA_USER /pyproject.toml /README.md /tmp/bmc/
COPY --from=bmc --chown=$MAMBA_USER:$MAMBA_USER /src/bmc /tmp/bmc/src/bmc
RUN pip install --no-deps /tmp/bmc && rm -rf /tmp/bmc

COPY --from=bmc --chown=$MAMBA_USER:$MAMBA_USER /meta/chelsa_gp_stac /app/meta/chelsa_gp_stac
COPY --chown=$MAMBA_USER:$MAMBA_USER create_cube.py /app/create_cube.py

ENV PYTHONUNBUFFERED=1 \
    BMC_OUTPUT_DIR=/output \
    BMC_CHELSA_CATALOG=/app/meta/chelsa_gp_stac/chelsa_master.parquet

VOLUME /output

# The base image's entrypoint script activates the conda environment first.
ENTRYPOINT ["/usr/local/bin/_entrypoint.sh", "python", "/app/create_cube.py"]
CMD ["--help"]
