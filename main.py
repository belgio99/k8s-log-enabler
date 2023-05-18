import os, sys

def checkIfKubernetesIsInstalled():
      print("Checking if Kubernetes is installed...")
      if os.system("kubectl version --short") == 0:
         print("Kubernetes is installed")
         return True
      else:
            print("Kubernetes is not installed")
            return False

def checkIfIstioIsInstalled():
      print("Checking if Istio is installed...")
      if os.system("istioctl version") == 0:
         print("Istio is installed")
         return True
      else:
            print("Istio is not installed")
            return False

def parseArgs():
    print("Parsing arguments...")
    argsNumber = len(sys.argv)
    if argsNumber!=2: 
          print("Error: wrong number of arguments")
          print("Usage: python3 progettotesi.py <Kubernetes YAML file to process>")
          sys.exit(1)
    else:
            print("Correct number of arguments")
            return sys.argv[1]
    
def openFile(kubernetesManifest):
      print("Opening file...")
      try:
            file = open(kubernetesManifest, "r")
            print("File opened correctly")
            return file
      except IOError:
            print("Error: file not found")
            sys.exit(1)



def main():
    print("PROGETTO TESI - LOG ANALYZER")
    print()
    checkIfKubernetesIsInstalled()
    yamlFile = parseArgs()
    #openFile(yamlFile)





if(__name__ == "__main__"):
    main()

