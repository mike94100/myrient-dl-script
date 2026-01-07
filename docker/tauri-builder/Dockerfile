FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential pkg-config git curl ca-certificates \
    libglib2.0-dev libgtk-3-dev libgdk-pixbuf2.0-dev libcairo2-dev \
    libpango1.0-dev libgirepository1.0-dev libwebkit2gtk-4.1-dev \
    libsoup2.4-dev libssl-dev cmake python3 sudo \
  && rm -rf /var/lib/apt/lists/*

# Install rustup and cargo
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Create workdir and copy project
WORKDIR /work
COPY . /work

# Build the tauri Rust crate (release)
WORKDIR /work/src-tauri
# Debug: list copied files to ensure Cargo.toml is present
RUN echo "--- /work contents ---" && ls -la /work || true
RUN echo "--- /work/src-tauri contents ---" && ls -la /work/src-tauri || true
RUN rustup default stable && cargo build --release

CMD ["/bin/bash"]
