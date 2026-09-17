import os
import shutil
import json

def setup_profile(src_profile_name, dest_profile_name):
    chrome_base = os.getenv("CHROME_USER_DATA_DIR", os.path.expanduser("~/.config/google-chrome"))
    gflow_base = os.getenv(
        "GFLOW_PROFILES_DIR",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".gflow", "profiles")
    )

    src_dir = os.path.join(chrome_base, src_profile_name)
    dest_dir = os.path.join(gflow_base, dest_profile_name)
    dest_default = os.path.join(dest_dir, "Default")

    print(f"Setting up {dest_profile_name} from {src_dir}...")

    if os.path.exists(dest_dir):
        print(f"Destination {dest_dir} already exists. Cleaning up...")
        shutil.rmtree(dest_dir)

    os.makedirs(dest_default, exist_ok=True)

    # 1. Prepare Local State
    with open(os.path.join(chrome_base, "Local State"), "r", encoding="utf-8") as f:
        chrome_local_state = json.load(f)
    with open(os.path.join(gflow_base, "default", "Local State"), "r", encoding="utf-8") as f:
        gflow_local_state = json.load(f)

    src_info = chrome_local_state.get("profile", {}).get("info_cache", {}).get(src_profile_name, {})

    # Copy profile info but mapped to "Default"
    dest_info = dict(src_info)
    dest_info["name"] = "Default"

    gflow_local_state["profile"] = {
        "info_cache": {
            "Default": dest_info
        },
        "last_active_profiles": ["Default"],
        "metrics": {"next_bucket_index": 2},
        "profiles_order": ["Default"],
        "last_used": "Default"
    }

    with open(os.path.join(dest_dir, "Local State"), "w", encoding="utf-8") as f:
        json.dump(gflow_local_state, f, indent=2)
    print(f"Wrote Local State for {dest_profile_name} (Email: {src_info.get('user_name')})")

    # 2. Copy profile directory files
    def ignore_patterns(path, names):
        ignored = []
        for name in names:
            if name.startswith("Singleton") or name.startswith("LOCK") or name == "DevToolsActivePort" or name in ["Cache", "Code Cache", "GPUCache", "DawnGraphiteCache", "DawnWebGPUCache"]:
                ignored.append(name)
        return ignored

    print(f"Copying files from {src_dir} to {dest_default}...")
    for item in os.listdir(src_dir):
        s = os.path.join(src_dir, item)
        d = os.path.join(dest_default, item)
        if item.startswith("Singleton") or item.startswith("LOCK") or item == "DevToolsActivePort" or item in ["Cache", "Code Cache", "GPUCache", "DawnGraphiteCache", "DawnWebGPUCache"]:
            continue
        try:
            if os.path.isdir(s):
                shutil.copytree(s, d, ignore=ignore_patterns, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)
        except Exception as e:
            print(f"  Warning copying {item}: {e}")

    print(f"Profile {dest_profile_name} initialized successfully.")

if __name__ == "__main__":
    setup_profile("Profile 3", "profile_3")
