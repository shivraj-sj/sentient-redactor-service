FROM public.ecr.aws/amazonlinux/amazonlinux:2023 AS rust_builder

ENV SHELL="/usr/bin/env bash"
RUN dnf upgrade -y
RUN dnf install -y git gcc pkgconfig openssl openssl-devel openssl-libs
RUN dnf install -y time which hostname

ENV RUST_LOG="debug"
ENV RUST_BACKTRACE="full"

ENV CARGO_HOME="$HOME/rust" RUSTUP_HOME="$HOME/rustup" PATH="$PATH:$HOME/rust/bin"
RUN curl -fsSL https://sh.rustup.rs | bash -is -- -y --verbose --no-modify-path --default-toolchain stable --profile minimal

WORKDIR /build

# Clone your repository
RUN git clone https://github.com/shivraj-sj/sentient-redactor-service.git .

# Build the Rust application
RUN cargo build --release

# Stage 2: Final runtime image
FROM public.ecr.aws/amazonlinux/amazonlinux:2023 AS runtime

ENV SHELL="/usr/bin/env bash"
ENV RUST_LOG="debug"
ENV RUST_BACKTRACE="full"

WORKDIR /apps

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
RUN python3 -m venv /apps/venv
ENV PATH="/apps/venv/bin:$PATH"

# Copy files from the build stage
COPY --from=rust_builder /build/requirements.txt /apps/
RUN /apps/venv/bin/pip install --upgrade pip
RUN /apps/venv/bin/pip install -r /apps/requirements.txt

# Install spacy and download the English model
RUN /apps/venv/bin/pip install spacy
RUN /apps/venv/bin/python -m spacy download en_core_web_sm

# Copy the built Rust binary from builder stage
COPY --from=rust_builder /build/target/release/sentient-redactor-service /apps/redactor-server

# Copy Python service files from build stage
COPY --from=rust_builder /build/presidio_service.py /apps/
COPY --from=rust_builder /build/test_client.py /apps/

# Copy demo files from build stage
COPY --from=rust_builder /build/demo*.txt /apps/
COPY --from=rust_builder /build/demo_files/ /apps/demo_files/

# Copy startup script from build stage
COPY --from=rust_builder /build/start.sh /apps/start.sh
RUN chmod +x /apps/start.sh

CMD tail -f /dev/null