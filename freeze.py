from cx_Freeze import setup, Executable

packages = ["os", "struct", "asyncio", "encodings",
            "aiortc", "aioice", "cffi", "idna"]
excludes = ["pydoc_data"]

build_exe_options = {
    "packages": packages,
    "excludes": excludes,
    "includes": packages,
    'include_files': [],
    'zip_include_packages': "*",
    'zip_exclude_packages': None,
    'include_msvcr': True,
    'constants': {}
}


setup(
    name="revpn",
    version="0.1",
    description="l2vpn over webrtc",
    options={"build_exe": build_exe_options},
    executables=[Executable("vpn.py")]
)
