if [ -n "$ZSH_VERSION" ]; then _src="${(%):-%x}"; else _src="${BASH_SOURCE[0]}"; fi
export NSO_DEMO="$(cd "$(dirname "$_src")/.." && pwd)"
export NSO_HOME="$NSO_DEMO/nso/current"
export NCS_RUN="$NSO_DEMO/nso/ncs-run"
export NETSIM_DIR="$NSO_DEMO/nso/netsim"
export NED_DIR="$(ls -d "$NSO_DEMO"/nso/neds/cisco-iosxr-cli-* 2>/dev/null | head -1)"
if [ -z "$JAVA_HOME" ] && command -v brew >/dev/null; then
  export JAVA_HOME="$(brew --prefix openjdk@17 2>/dev/null)/libexec/openjdk.jdk/Contents/Home"
fi
source "$NSO_HOME/ncsrc"
echo "NCS_DIR=$NCS_DIR  NED_DIR=$NED_DIR"