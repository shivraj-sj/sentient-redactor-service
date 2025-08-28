# Multi-stage Dockerfile for Sentient Redactor Service
# Designed for AWS Nitro Enclaves

# Stage 1: Build Rust application
FROM public.ecr.aws/amazonlinux/amazonlinux:2023 as rust_builder

ENV SHELL="/usr/bin/env bash"

RUN dnf upgrade -y
RUN dnf install -y git gcc pkgconfig openssl openssl-devel openssl-libs
RUN dnf install -y time which hostname

ENV RUST_LOG="debug"
ENV RUST_BACKTRACE="full"

ENV CARGO_HOME="$HOME/rust" RUSTUP_HOME="$HOME/rustup" PATH="$PATH:$HOME/rust/bin"
RUN curl -fsSL https://sh.rustup.rs | bash -is -- -y --verbose --no-modify-path --default-toolchain stable --profile minimal

# Specify path relative to the build context
WORKDIR /app-builder

# Option 1: Use remote repository (uncomment the line below)
# RUN git clone https://github.com/shivraj-sj/sentient-redactor-service.git
# Option 2: Use local code (copy from build context)
COPY . /app-builder

# Build the Rust application
RUN cargo build --release

# Stage 2: Final runtime image
FROM public.ecr.aws/amazonlinux/amazonlinux:2023 as runtime

ENV SHELL="/usr/bin/env bash"
ENV RUST_LOG="debug"
ENV RUST_BACKTRACE="full"

WORKDIR /app

RUN dnf upgrade -y

RUN dnf install -y kernel-libbpf systemd systemd-libs systemd-resolved initscripts
RUN dnf install -y /usr/bin/systemctl

RUN dnf install -y sudo time which hostname tar bsdtar cpio findutils pcre-tools pciutils procps-ng
RUN dnf install -y iputils iproute dnsmasq bind bind-utils bind-dnssec-utils traceroute net-tools socat nc nmap-ncat
RUN dnf install -y kmod kmod-libs
RUN dnf install -y nftables iptables iptables-nft iptables-libs iptables-utils iptables-legacy iptables-legacy-libs
RUN dnf install -y lsof perf iperf iperf3
RUN dnf install -y --allowerasing curl
RUN dnf install -y jq wget openssh git rsync
RUN dnf install -y lynx w3m
RUN dnf install -y awscli

# Install Python dependencies and build tools
RUN dnf install -y python3 python3-pip python3-devel
RUN dnf install -y gcc gcc-c++ make

# Create and activate virtual environment
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Copy Python requirements and install dependencies
COPY requirements.txt /app/
RUN /app/venv/bin/pip install --upgrade pip
RUN /app/venv/bin/pip install -r requirements.txt

# Install spacy and download the English model
RUN /app/venv/bin/pip install spacy
RUN /app/venv/bin/python -m spacy download en_core_web_sm

# Copy the built Rust binary from builder stage
COPY --from=rust_builder /app-builder/target/release/sentient-redactor-service /app/

# Copy Python service files
COPY presidio_service.py /app/
COPY test_client.py /app/

# Copy demo files (optional)
COPY demo*.txt /app/
COPY demo_files/ /app/demo_files/

# Create startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Expose ports
EXPOSE 3000 8001


# Start both services in background and keep container running
CMD ["/bin/bash", "-c", "/app/start.sh & tail -f /dev/null"]
