
import argparse
import subprocess
from os import getcwd, listdir, path
from textwrap import dedent

import yaml
import sys




class DirectoryNotFoundError(FileNotFoundError): pass



def composeStackFile(stack: str) -> str:
	"""
	Get the Docker Compose filename for the given stack, assuming it exists.
	
	Arguments
	---------
		stack (str) : Docker Compose stack name
	"""
	return f'docker-compose.{stack}.yml'

def checkComposeStackExists(stack: str) -> bool:
	"""
	Check if the given stack's Docker Compose file exists.
	
	Arguments
	---------
		stack (str) : Docker Compose stack name
	"""
	composeFile = getcwd() + '/' + composeStackFile(stack)
	sys.stderr.write(f'Using {composeFile}\n')
	return path.exists(composeFile)

def getStacksInDir() -> list[str]:
	"""Get the Docker Compose files (stacks) in the current directory."""
	listing = listdir(getcwd())
	stacks = []

	for l in listing:
		if len(ls := l.split('.')) >= 3 \
				and ls[0] == 'docker-compose' \
				and ls[2] == ('yml' or 'yaml'):
			stacks.append(ls[1])
	
	return stacks

def getServicesInStack(stack: str) -> list[str]:
	"""Get the service names defined in the given stack."""
	with open(getcwd() + '/' + composeStackFile(stack), 'r') as f:
		dcf: dict[str, dict[str, dict]] = yaml.safe_load(f)
	
	services = list(dcf['services'].keys())
	return services


def runCommand(args: argparse.Namespace, command: list, toStdOut=False, quiet=False):
	"""
	Check if the stack given via CLI exists, then run the given command list via `subprocess.run()`, printing an error if the stack does not exist.

	Arguments
	---------
		args (argparse.Namespace) : parsed command-line arguments from `argparse`.
		command (list) : command list containing the program name and all arguments.
		toStdOut (bool, False) : return the stdout and stderr of the command. Removes all formatting in the process.
		quiet (bool, False) : Do not print the output of the command.
	"""
	if checkComposeStackExists(args.stack):
		if not toStdOut:
			subprocess.run(command)
		else:
			out = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='UTF-8')
			if not quiet:
				print(out.stdout)
			return out
	else:
		print(f'Docker compose file {composeStackFile(args.stack)} for stack {args.stack} is not present in the current directory.')
		exit(2)


def proceed(args: argparse.Namespace, message: str, default=True) -> bool:
	"""
	Ask the user if they would like to proceed using the given message.

	Arguments
	---------
		message (str) : message to display to user
		default (bool) : default option; True = yes, False = no
	"""
	if not args.alwaysConfirm:
		if default == True:
			choices = ' [Y/n] '
		else:
			choices = ' [y/N] '

		resp = input(message + choices)

		if default == True:
			if resp.lower() == ('y' or 'yes' or ''):
				return True
			else:
				return False
		else:
			if resp.lower() == ('y' or 'yes'):
				return True
			else:
				return False
	else:
		return args.alwaysConfirm



def start(args: argparse.Namespace):
	command = ['docker', 'compose', '-f', composeStackFile(args.stack), 'up', '-d']
	runCommand(args, command)


def stop(args: argparse.Namespace):
	command = ['docker', 'compose', '-f', composeStackFile(args.stack), 'down']
	runCommand(args, command)


def status(args: argparse.Namespace):
	command = ['docker', 'compose', '-f', composeStackFile(args.stack), 'ps']
	if args.asJson:
		command += ['--format', 'json']
		out = runCommand(args, command, toStdOut=True, quiet=True)
		# sends output of `docker compose ps status` to `jq` for formatting
		subprocess.run('jq', input=out.stdout, encoding='UTF-8') #type:ignore
	else:
		runCommand(args, command)


def execute(args: argparse.Namespace):
	command = ['docker', 'compose', '-f', composeStackFile(args.stack), 'exec', args.service, args.command] + args.subargs
	runCommand(args, command)


def manage(args: argparse.Namespace):
	args.stack = 'site'
	command = ['docker', 'compose', '-f', composeStackFile(args.stack), 'exec', 'gunicorn', 'python', 'manage.py'] + args.subargs
	runCommand(args, command)


def build(args: argparse.Namespace):
	command = ['docker', 'compose', '-f', composeStackFile(args.stack), 'build']
	if args.service:
		command.append(args.service)
	
	runCommand(args, command)


def logs(args: argparse.Namespace):
	command = ['docker', 'compose', '-f', composeStackFile(args.stack), 'logs']
	if args.follow:
		command.append('--follow')
	if args.service:
		command.append(args.service)

	runCommand(args, command)



def _validateRepo(url: str):
	urlSplit = url.split('/')
	if len(urlSplit) >= 5:
		return urlSplit[0] == 'http:' or urlSplit[0] == 'https:'
	else:
		return False
	


def prep(args: argparse.Namespace):
	"""
	Makes sure all required files are in this folder, then creates the '.env' file containg settings for Docker Compose, Gunicorn, and PostgreSQL.
	"""
	args.stack = 'site'
	thisFolder = getcwd()
	thisHostnameOut = runCommand(args, ['hostnamectl', '--static'], toStdOut=True, quiet=True)

	if thisHostnameOut.stdout == '': #type:ignore
		thisHostname = "this server's hostname"
	else:
		thisHostname = thisHostnameOut.stdout[:-1] #type:ignore

	shouldExist_files = ['docker-compose.site.yml', 'instructions.md']
	shouldExist_folders: list[str] = []

	print('Making sure all the right folders and files are present... ')
	for fileName in shouldExist_files:
		if not path.isfile(thisFolder + '/' + fileName): 
			raise FileNotFoundError(f'Required file {fileName} not present in group folder {thisFolder}.')
		else:
			print(f"  - found {fileName}")
	
	for folderName in shouldExist_folders:
		if not path.isdir(thisFolder + '/' + folderName):
			raise DirectoryNotFoundError(f'Required folder {folderName} is not present in group folder {thisFolder}.')
		else:
			print(f"  - found {folderName}/")
	print('Found them all!\n')


	if not args.gitRepo:
		repoIsValid = False
		while not repoIsValid:
			gitRepo = input("Enter the full URL to your group's GitHub repo: ")
			repoIsValid = _validateRepo(gitRepo)
			if not repoIsValid: print('Repo is not a valid url.', end=' ')
	else:
		gitRepo = args.gitRepo
	
	print('Cloning repo...')
	runCommand(args, ['rm', '-rf', 'site'], quiet=True)
	subprocess.run(['git', 'clone', gitRepo, 'site'], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

	
	if not args.pfName:
		expectedProjectFolders = ['django', 'django_site', 'django_project', 'dj']
		pfName = ''
		found = False
		auto = False
		for pf in expectedProjectFolders:
			found = path.isdir(thisFolder + '/site/' + pf)
			if found:
				auto = True
				pfName = pf
				break
		
		if not found:
			pfName = input('Django project folder not detected automatically in the site folder. Please enter the name of the Django project folder (ex: django_project, dj): ')
			while not path.isdir(thisFolder + '/site/' + pfName):
				pfName = input('Given Django project folder does not exist in the site folder. Please enter the name of the Django project folder (ex: django_project, dj): ')
				
	else:
		pfName = args.pfName

	
	if not args.groupName:
		groupName = input('Enter the name of your group. It should be the name of this folder: ')
	else:
		groupName = args.groupName

	if not args.siteName:
		siteName = input("Enter the name of your site (ex: takethebus, spaceweather, etc.). Keep it simple, as this will be in your site's URL! : ")
	else:
		siteName = args.siteName


	print(f'\n---\nGroup name: {groupName}')
	print(f'Site name: {siteName}')
	print(f'Django project folder: {pfName} {'(detected automatically)' if auto else ''}')
	print(f'Git repo URL: {gitRepo}\n---\n')

	if proceed(args, 'Confirm these setttings?'):
		postgresPassword = runCommand(args, ['pwgen', '32', '1'], toStdOut=True, quiet=True).stdout #type:ignore
		envConf = dedent(
			f"""\
			GROUP_NAME={groupName}

			SITE_NAME={siteName}
			# may be called 'django', 'django_site', 'django_project', 'dj', etc.
			SITE_FOLDER={pfName}

			POSTGRES_PASSWORD={postgresPassword}
			"""
		)

		print("Writing configuration to '.env'...", end=' ')
		with open(thisFolder + '/.env', 'w+') as envFile:
			envFile.write(envConf)
		print('done!')

		print(f"Make sure you add {thisHostname} to the ALLOWED_HOSTS list in settings.py!")

	else:
		print('Canceling!')
		exit(1)



if __name__ == '__main__':
	print('This file is not meant to be ran directly.')
	exit(2)
