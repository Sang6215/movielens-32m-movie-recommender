"""Manage a project-local, single-node HDFS on Windows without changing the OS.

Apache's distribution is verified against its published SHA-512 checksum.
Existing NameNode storage is never formatted again. Runtime/data/logs stay in
the ignored .hadoop directory; this script is the reproducible source artifact.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tarfile
import time
import urllib.request
from xml.etree.ElementTree import Element, SubElement, ElementTree

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".hadoop"
RUNTIME = LOCAL / "runtime"
CONF = LOCAL / "conf"
VERSION = "3.3.4"  # Matches the Hadoop client bundled with PySpark 3.5.7.
BASE_URL = f"https://archive.apache.org/dist/hadoop/common/hadoop-{VERSION}"
JAVA_CLASSES = {
    "namenode": "org.apache.hadoop.hdfs.server.namenode.NameNode",
    "datanode": "org.apache.hadoop.hdfs.server.datanode.DataNode",
}


def ascii_root() -> Path:
    """Use a reversible drive alias for Java 8/Windows native Unicode paths."""
    if str(ROOT).isascii():
        return ROOT
    saved = LOCAL / "drive.json"
    if saved.exists():
        letter = json.loads(saved.read_text(encoding="utf-8"))["letter"]
        drive = Path(letter + "/")
        if drive.exists() and drive.samefile(ROOT):
            return drive
    for letter in "RSTUVWXYZ":
        drive = Path(letter + ":/")
        if drive.exists():
            if drive.samefile(ROOT):
                return drive
            continue
        subst = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32/subst.exe"
        subprocess.run([str(subst), letter + ":", str(ROOT)], check=True)
        if not drive.exists() or not drive.samefile(ROOT):
            raise RuntimeError("Cannot validate the temporary ASCII drive alias.")
        LOCAL.mkdir(exist_ok=True)
        saved.write_text(json.dumps({"letter": letter + ":", "root": str(ROOT)}, ensure_ascii=False), encoding="utf-8")
        print(f"Java path alias: {letter}: -> project directory", flush=True)
        return drive
    raise RuntimeError("No free drive letter for Java's ASCII path alias.")


def download_archive(archive: Path) -> None:
    url = f"{BASE_URL}/{archive.name}"
    with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=60) as response:
        size = int(response.headers["Content-Length"])
    # Reuse a partial sequential download and retrieve the remaining byte ranges.
    prefix = archive.with_suffix(".part")
    received = prefix.stat().st_size if prefix.exists() else 0
    parts_dir = LOCAL / "download_parts"
    parts_dir.mkdir(exist_ok=True)
    ranges = [(start, min(start + 32 * 1024**2, size) - 1)
              for start in range(received, size, 32 * 1024**2)]

    def fetch(bounds: tuple[int, int]) -> Path:
        start, end = bounds
        part = parts_dir / f"{start}-{end}"
        if part.exists() and part.stat().st_size == end - start + 1:
            return part
        request = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}"})
        with urllib.request.urlopen(request, timeout=60) as response:
            if response.status != 206 or response.headers.get("Content-Range") != f"bytes {start}-{end}/{size}":
                raise RuntimeError("Apache server did not return the requested download range.")
            with part.open("wb") as target:
                shutil.copyfileobj(response, target, length=1024**2)
        if part.stat().st_size != end - start + 1:
            raise RuntimeError("Incomplete Hadoop download range; rerun install.")
        print(f"Downloaded range {start // 1024**2}–{(end + 1) // 1024**2} MiB", flush=True)
        return part

    with ThreadPoolExecutor(max_workers=8) as pool:
        parts = list(pool.map(fetch, ranges))
    combined = archive.with_suffix(".combine.tmp")
    with combined.open("wb") as target:
        if prefix.exists():
            with prefix.open("rb") as stream:
                shutil.copyfileobj(stream, target)
        for part in parts:
            with part.open("rb") as stream:
                shutil.copyfileobj(stream, target)
    if combined.stat().st_size != size:
        raise RuntimeError("Incomplete Hadoop archive.")
    combined.replace(archive)
    for part in parts:
        part.unlink()
    if prefix.exists():
        prefix.unlink()


def install() -> None:
    if (RUNTIME / "share/hadoop/hdfs" / f"hadoop-hdfs-{VERSION}.jar").exists():
        print("Hadoop runtime already installed.")
        return
    LOCAL.mkdir(exist_ok=True)
    archive = LOCAL / f"hadoop-{VERSION}.tar.gz"
    published = urllib.request.urlopen(f"{BASE_URL}/{archive.name}.sha512", timeout=60).read().decode()
    match = re.search(r"\b[0-9a-fA-F]{128}\b", published)
    if match is None:
        raise RuntimeError("Cannot parse Apache's published SHA-512 checksum.")
    checksum = match.group(0)
    if not archive.exists():
        download_archive(archive)
    with archive.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha512").hexdigest()
    if actual.lower() != checksum.lower():
        raise RuntimeError("Apache archive SHA-512 mismatch. Do not use this archive.")
    print("SHA-512 verified. Extracting Common and HDFS runtime...", flush=True)
    with tarfile.open(archive, "r:gz") as source:
        for member in source:
            parts = Path(member.name).parts
            if len(parts) < 3 or parts[1:3] not in (("share", "hadoop"), ("etc", "hadoop")):
                continue
            relative = Path(*parts[1:])
            if relative.parts[:2] == ("share", "hadoop") and len(parts) > 3 and parts[3] not in ("common", "hdfs"):
                continue
            if not member.isfile():
                continue
            destination = (RUNTIME / relative).resolve()
            if not destination.is_relative_to(RUNTIME.resolve()):
                raise RuntimeError("Unsafe archive member.")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with source.extractfile(member) as stream, destination.open("wb") as output:
                shutil.copyfileobj(stream, output)
    print(f"Installed Apache Hadoop {VERSION} into .hadoop/runtime")


def configure() -> None:
    CONF.mkdir(parents=True, exist_ok=True)
    local_alias = ascii_root() / ".hadoop"
    properties = {
        "core-site.xml": {
            "fs.defaultFS": "hdfs://127.0.0.1:9000",
            "hadoop.tmp.dir": (local_alias / "tmp").as_posix(),
        },
        "hdfs-site.xml": {
            "dfs.replication": "1",
            "dfs.namenode.name.dir": (local_alias / "dfs/name").as_uri(),
            "dfs.datanode.data.dir": (local_alias / "dfs/data").as_uri(),
            "dfs.namenode.rpc-address": "127.0.0.1:9000",
            "dfs.namenode.http-address": "127.0.0.1:9870",
            "dfs.datanode.address": "127.0.0.1:9866",
            "dfs.datanode.http.address": "127.0.0.1:9864",
            "dfs.datanode.ipc.address": "127.0.0.1:9867",
            "dfs.datanode.hostname": "127.0.0.1",
            "dfs.client.use.datanode.hostname": "true",
            "dfs.namenode.datanode.registration.ip-hostname-check": "false",
        },
    }
    for filename, values in properties.items():
        root = Element("configuration")
        for name, value in values.items():
            prop = SubElement(root, "property")
            SubElement(prop, "name").text = name
            SubElement(prop, "value").text = value
        ElementTree(root).write(CONF / filename, encoding="utf-8", xml_declaration=True)
    shutil.copyfile(RUNTIME / "etc/hadoop/log4j.properties", CONF / "log4j.properties")


def java_command(main_class: str, *args: str) -> tuple[list[str], dict[str, str]]:
    if not (LOCAL / "bin/winutils.exe").exists() or not (LOCAL / "bin/hadoop.dll").exists():
        raise RuntimeError("Windows requires winutils.exe and hadoop.dll in .hadoop/bin (existing Spark setup).")
    java_home = os.environ.get("JAVA_HOME")
    java = str(Path(java_home) / "bin/java.exe") if java_home else shutil.which("java")
    if not java or not Path(java).exists():
        raise RuntimeError("Java 8 or Java 11 is required.")
    # Java 8's Windows launcher can lose Vietnamese characters in absolute
    # command-line paths. ASCII relative paths with an explicit cwd avoid that.
    classpath = os.pathsep.join(os.path.relpath(path, ROOT) for path in (
        CONF,
        RUNTIME / "share/hadoop/common/*",
        RUNTIME / "share/hadoop/common/lib/*",
        RUNTIME / "share/hadoop/hdfs/*",
        RUNTIME / "share/hadoop/hdfs/lib/*",
    ))
    local_alias = ascii_root() / ".hadoop"
    env = dict(os.environ, HADOOP_HOME=str(local_alias), HADOOP_CONF_DIR=str(local_alias / "conf"))
    env["PATH"] = str(local_alias / "bin") + os.pathsep + env.get("PATH", "")
    command = [java, "-Xmx1g", "-Djava.library.path=.hadoop/bin",
               "-Dhadoop.log.dir=.hadoop/logs", "-Dhadoop.log.file=hdfs.log",
               "-cp", classpath, main_class, *args]
    return command, env


def run_hdfs(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    command, env = java_command("org.apache.hadoop.hdfs.tools.DFSAdmin" if args[0] == "dfsadmin"
                                else "org.apache.hadoop.fs.FsShell", *args[1:])
    return subprocess.run(command, env=env, cwd=ascii_root(), check=check)


def start(foreground: bool = False) -> None:
    install()
    configure()
    (LOCAL / "logs").mkdir(exist_ok=True)
    name_dir = LOCAL / "dfs/name"
    version_file = name_dir / "current/VERSION"
    if not version_file.exists():
        if name_dir.exists() and any(name_dir.iterdir()):
            raise RuntimeError("NameNode directory contains data without VERSION. Refusing to format it.")
        command, env = java_command(JAVA_CLASSES["namenode"], "-format", "-nonInteractive")
        with (LOCAL / "logs/format.log").open("ab") as log:
            result = subprocess.run(command, env=env, cwd=ascii_root(), stdout=log, stderr=log)
        if result.returncode:
            raise RuntimeError("NameNode format failed. See .hadoop/logs/format.log.")
        print("Formatted new NameNode storage.", flush=True)
    processes = {}
    existing_path = LOCAL / "processes.json"
    if existing_path.exists():
        processes = json.loads(existing_path.read_text())
    children = []
    for service, main_class in JAVA_CLASSES.items():
        port = 9000 if service == "namenode" else 9866
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                if service not in processes:
                    raise RuntimeError(f"Port {port} is already occupied by a different service.")
                print(f"{service} is already running.")
                continue
        except OSError:
            pass
        command, env = java_command(main_class)
        with (LOCAL / f"logs/{service}.out.log").open("ab") as log:
            process = subprocess.Popen(command, env=env, cwd=ascii_root(), stdout=log, stderr=log,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
        processes[service] = process.pid
        children.append(process)
        existing_path.write_text(json.dumps(processes, indent=2))
        print(f"Started {service}, PID {process.pid}", flush=True)
    print("NameNode UI: http://127.0.0.1:9870 ; run status after startup.")
    if foreground:
        print("Keeping HDFS running in this terminal. Ctrl+C stops the managed daemons.", flush=True)
        try:
            while True:
                if any(child.poll() is not None for child in children):
                    raise RuntimeError("HDFS daemon exited. Check .hadoop/logs/*.out.log.")
                time.sleep(1)
        finally:
            stop()


def stop() -> None:
    process_file = LOCAL / "processes.json"
    if not process_file.exists():
        print("No managed HDFS process recorded.")
        return
    processes = json.loads(process_file.read_text())
    for service in ("datanode", "namenode"):
        pid = processes.get(service)
        if not pid:
            continue
        # Validate the command line before stopping a potentially reused PID.
        result = subprocess.run(["powershell", "-NoProfile", "-Command",
                                 f"(Get-CimInstance Win32_Process -Filter 'ProcessId={int(pid)}').CommandLine"],
                                capture_output=True, text=True)
        if JAVA_CLASSES[service] in result.stdout:
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=False, capture_output=True)
            print(f"Stopped {service} ({pid}).")
    process_file.unlink()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "start", "status", "stop", "dfs"))
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.action == "install":
        install()
    elif args.action == "start":
        start(foreground="--foreground" in args.arguments)
    elif args.action == "stop":
        stop()
    elif args.action == "status":
        run_hdfs("dfsadmin", "-report")
    else:
        run_hdfs("dfs", *args.arguments)


if __name__ == "__main__":
    main()
