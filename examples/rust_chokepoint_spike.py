"""Rust Chokepoint Spike example — v0.4。

Shows:
- write_text request
- read_text request
- path traversal denial
- structured result

Requires: Rust binary at crates/koguchi-chokepoint/target/debug/koguchi-chokepoint
Build: cargo build --manifest-path crates/koguchi-chokepoint/Cargo.toml
"""

from pathlib import Path

from koguchi.chokepoint_client import RustChokepointClient

BINARY_PATH = Path("crates/koguchi-chokepoint/target/debug/koguchi-chokepoint")


def main() -> None:
    if not BINARY_PATH.exists():
        print("Rust binary not found. Build it first:")
        print("  cargo build --manifest-path crates/koguchi-chokepoint/Cargo.toml")
        return

    client = RustChokepointClient(BINARY_PATH.resolve())

    print("=== write_text ===")
    r = client.execute("write_text", Path("/tmp"), "koguchi-spike.txt",
                        content="hello from rust chokepoint", request_id="ex-1")
    print(f"  allowed={r.allowed} status={r.status}")

    print("=== read_text ===")
    r = client.execute("read_text", Path("/tmp"), "koguchi-spike.txt",
                        request_id="ex-2")
    print(f"  allowed={r.allowed} stdout={r.stdout.rstrip()}")

    print("=== path traversal denied ===")
    r = client.execute("write_text", Path("/tmp"), "../evil.txt",
                        request_id="ex-3")
    print(f"  allowed={r.allowed} error={r.error}")

    # cleanup
    Path("/tmp/koguchi-spike.txt").unlink(missing_ok=True)
    print("\nDone.")


if __name__ == "__main__":
    main()
