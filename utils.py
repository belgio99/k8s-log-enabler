import os, sys


def checkInstallation():
    print("\nChecking installation...\n")
    components = ["kubectl", "istioctl"]
    for component in components:
        print("Checking " + component + "...")
        if os.system(component + " version > /dev/null 2>&1") != 0:
            print(component + " is not installed")
            sys.exit(1)
    print("\nAll components are installed\n")