import requests
from requests import Response
import re
import os
import json
from tqdm import tqdm
import argparse

rootPath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+"/Mods"
repos = [
    #twrp
    {"github": "corsicanu/TWRP_Bootlogo_patcher"},

    # modules
    {"github": "PerformanC/ReZygisk",                  "formatName": False},
    {"github": "JingMatrix/LSPosed",                   "require": "zygisk"},

    # apps
    {"github": "KieronQuinn/AmbientMusicMod"},
    {"github": "reveny/Android-Native-Root-Detector"}, 
    {"github": "KieronQuinn/PixelLauncherMods"},       
    {"github": "AndroidAudioMods/ViPER4Android",       "formatName": False,   "formatAuthor": False},
    {"github": "WSTxda/ViperFX-RE-Releases",           "formatName": False,   "formatAuthor": False},
    {"github": "Dr-TSNG/Hide-My-Applist",              "require": "lsposed"},
    {"github": "zhanghai/MaterialFiles",               "file": "*apk"},
    {"github": "termux/termux-app",                    "file": "*v8a*"},
    {"github": "tiann/KernelSU",                       "file": "*apk",        "version": "v1.0.1"},
]

def getDetailsJson(path: str) -> dict:
    try:
        with open(f"{rootPath}/{path}/details.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def saveDetailsJson(path: str, data: dict) -> None:
    details_path = f"{rootPath}/{path}/details.json"
    if os.path.exists(details_path):
        os.remove(details_path)
    with open(details_path, "w") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

def setDetails(key: str, value: str, details: dict) -> None:
    if key not in details:
        details[key] = value
    details[key] = value


def getHTML(repo: str = "revanced-apks/build-apps", version:str = None) -> str:
    url = f"https://github.com/{repo}/releases/{'tag/' + version if version else 'latest'}"
    response = requests.get(url, allow_redirects=True)
    if response.status_code == 200:
        return response
    else:
        raise Exception(f"Failed to get HTML. Status code: {response.status_code} {url}")


def updateFileList() -> str:
    dirs = [d for d in os.listdir(rootPath) if os.path.isdir(os.path.join(rootPath, d))]
    dirString = ",".join(dirs)

    with open(os.path.join(rootPath, "list"), "w") as file:
        file.write(dirString)
    return os.path.join(rootPath, "list")

def getREADME(repo: str = "revanced-apks/build-apps") -> str:
    url = f"https://github.com/{repo}"
    response = requests.get(url, allow_redirects=True)
    if response.status_code == 200:
        start = response.text.find('repos-overview')
        if start == -1:
            raise Exception("Failed to find 'repos-overview' in the response.")
        
        script_start = response.text.find('<script type="application/json"', start)
        if script_start == -1:
            raise Exception("Failed to find the JSON script tag in the response.")
        
        script_end = response.text.find('</script>', script_start)
        if script_end == -1:
            raise Exception("Failed to find the end of the JSON script tag in the response.")
        
        json_data = response.text[script_start:script_end]
        json_start = json_data.find('>') + 1
        filesJson = json_data[json_start:]

        readme_end = filesJson.find("preferredFileType")-3
        readme_start = filesJson[:readme_end].rfind('path":"')+7
        readme_name = filesJson[readme_start:readme_end]
        readme_path = f"https://raw.githubusercontent.com/{repo}/HEAD/{readme_name}"

        response = requests.get(readme_path, allow_redirects=True)
        
        if response.status_code == 200:
            return response.text
        else:
            raise Exception(f"Failed to get README content. Status code: {response.status_code}")
    else:
        raise Exception(f"Failed to get README. Status code: {response.status_code}")


def getChangeLog(html: str) -> str:
    return html[html.find('class="markdown-body my-3">')+27:html.find("</div>", html.find('class="markdown-body my-3">')+27)]

def getFile(html: str, filename_pattern: str, path: str) -> str:
    assetsLink = html[html.rfind('"', 0, html.find("expanded_assets/")) + 1:html.find('"', html.find("expanded_assets/"))]

    response = requests.get(assetsLink, allow_redirects=True)
    if response.status_code == 200:
        pattern = r'[a-zA-Z0-9\.\-_\/\+]+\/releases\/download\/[a-zA-Z0-9\.\-_\/\+]+'
        links = re.findall(pattern, response.text)
        matched_links = [link for link in links if re.search(filename_pattern.replace('*', '.*'), link)]
        if len(matched_links) == 1:
            file_url = f"https://github.com{matched_links[0]}"
            local_file_path = os.path.join(rootPath, path, "file")
            file_response = requests.get(file_url, allow_redirects=True)
            if file_response.status_code == 200:
                file_path = os.path.join(rootPath, path, "file")
                with open(file_path, 'wb') as file:
                    file.write(file_response.content)
                    return file_path
            else:
                raise Exception(f"Failed to download the file. Status code: {file_response.status_code}")
        elif len(matched_links) > 1:
            print("Possible matched links:")
            for link in matched_links:
                print(f"https://github.com{link}")
            raise Exception("Error: Multiple files matched the pattern.")
        else:
            print("Possible links:")
            for link in links:
                print(f"https://github.com{link}")
            raise Exception("Error: No files matched the pattern.")
    else:
        raise Exception(f"Failed to get assets link. Status code: {response.status_code}")

def getVersion(url: str) -> str:
    version = url.split('/')[-1]
    return version

def formatString(string: str) -> str:
    string = string.replace("-", " ").replace("_", " ")
    formatedString = ""
    for index, char in enumerate(string):
        if char.isupper() and not index == 0 and not string[index-1].isupper() and not string[index-1] == " ":
            formatedString += " "
        formatedString += char
    capitlizedString = ""
    for index, char in enumerate(formatedString):
        if index == 0: capitlizedString += char.capitalize()
        elif formatedString[index-1] == " ": capitlizedString += char.capitalize()
        else: capitlizedString += char
    return capitlizedString

def getAuthor(url: str, formated: bool = False) -> str:
    author = url.split('/')[-2]
    if formated:
        author = formatString(author)
    return author

def getName(url: str, formated: bool = False) -> str:
    name = url.split('/')[-1]
    if formated:
        name = formatString(name)
    return name

def getAPKPackageName(path: str) -> str:
    aapt_output = os.popen(f"aapt dump badging {rootPath}/{path}/file").read()
    match = re.search(r"package: name='([^']+)'", aapt_output)
    if match:
        return match.group(1)
    else:
        raise Exception("Failed to extract package name using aapt.")

def getType(path:str) -> str:
    fullPath = os.path.join(rootPath, path, "file")
    unzip_output = os.popen(f"unzip -l {fullPath}").read()
    if "AndroidManifest.xml" in unzip_output:
        return "apk"
    if "module.prop" in unzip_output:
        return "module"
    else:
        return "twrp"

def getNumbImages(path: str) -> int:
    fullPath = os.path.join(rootPath, path)
    return len([name for name in os.listdir(fullPath) if os.path.isfile(os.path.join(fullPath, name)) and re.match(r'^\d+\.jpg$', name)])


parser = argparse.ArgumentParser(description="Update GitHub repositories.")
parser.add_argument('--force', action='store_true', help="Force update the repositories.")
args = parser.parse_args()

force_update = args.force 

progress_bar = tqdm(repos, desc="Updating repositories")
for repo in progress_bar:
    repo_name = getName(repo["github"])
    progress_bar.set_description(f"Updating {repo_name}")
    try:
        os.makedirs(os.path.join(rootPath, repo_name), exist_ok=True)

        details = getDetailsJson(repo_name)
        response = getHTML(repo["github"], repo.get("version", None))

        if not force_update and details.get("version") == getVersion(response.url):
            continue

        getFile(response.text, repo.get("file", ""), repo_name)
        repo["type"] = getType(repo_name)

        setDetails("name", getName(repo["github"], repo.get("formatName", True)), details)
        setDetails("author", getAuthor(repo["github"], repo.get("formatAuthor", True)), details)
        setDetails("version", getVersion(response.url), details)
        setDetails("updateTypeString", repo['type'], details)
        setDetails("srcLink", f"https://github.com/{repo['github']}" ,details)
        if "keywords" not in details: details["keywords"] = [repo["type"]]


        if "require" in repo: details["require"] = repo["require"]
        if repo["type"] == "apk": setDetails("openName", getAPKPackageName(repo_name), details)
        if repo.get("require") == "lsposed": setDetails("openName", "com.lspd", details)
        if repo["type"] == "apk": setDetails("packageName", getAPKPackageName(repo_name), details)

        details["images"] = getNumbImages(repo_name)
        setDetails("README", getREADME(repo["github"]), details)
        setDetails("changeLog", getChangeLog(response.text), details)
        
        saveDetailsJson(repo_name, details)

    except Exception as e:
        print(f"\033[91m{e}\033[0m")
        raise e
        continue

updateFileList()
progress_bar.close()