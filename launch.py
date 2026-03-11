import sys, os, subprocess, time, psycopg2, yaml

from pathlib import Path
from collections import namedtuple

NAME = 'DondeSiempre Launcher'

MVNW = 'mvnw.cmd' if os.name == 'nt' else './mvnw'
NPM = 'npm.cmd' if os.name == 'nt' else 'npm'
NPX = 'npx.cmd' if os.name == 'nt' else 'npx'

CWD = Path(os.getcwd())
CFG = (CWD / 'launch.cfg')

DB_RETRY_SECONDS = 0.5

ARGS = {
    'RESET': ['-r', '--reset'],
    'STOP': ['-s', '--stop'],
    'NO_DB': ['-n', '--nodb'],
    'GEN_MIGR': ['-g, --gen'],
    'NO_CACHE': ['-n, --nocache'],
    'DOCKER': ['-d', '--docker']
}

Container = namedtuple('Container', ['port', 'user', 'password', 'db'])

'''
UTILS
'''
def get_key(key):
    out = None

    if not os.path.exists(CFG):
        print('Configuration file not found, creating empty configuration file...')

        with open(CFG, mode = 'w', encoding = 'utf-8') as f:
            f.write('BACKEND_PATH = /path/to/backend\n')
            f.write('FRONTEND_PATH = /path/to/frontend\n')
        print(f'Configuration file created at {CFG}')
        print('Please set the BACKEND_PATH and FRONTEND_PATH keys as needed.')
        return out

    with open(CFG, mode = 'r', encoding = 'utf-8') as f:
        for line in f.readlines():
            if '=' not in line:
                continue

            chunks = [c.strip() for c in line.split('=')]

            if key in chunks[0]:
                out = chunks[1]
                break

    if out == None:
        print(f'Error: Key {key} not set in {CFG}')
    return out

def parse_docker_compose(path):
    out = dict()

    with open(path / 'docker-compose.yml', mode = 'r') as f:
        data = yaml.safe_load(f)
        
        for service in data['services']:
            container = Container(
                int(data['services'][service]['ports'][0].split(':')[0].strip().replace('"', '')),
                data['services'][service]['environment']['POSTGRES_USER'].strip(),
                data['services'][service]['environment']['POSTGRES_PASSWORD'].strip(),
                data['services'][service]['environment']['POSTGRES_DB'].strip()
            )
            out[service] = container
    return out

def check_db(container):
    out = False

    print('Checking database connectivity...')
    start = time.time()

    while not out and (time.time() - start) < 60:
        try:
            connection = psycopg2.connect(
                dbname = container.db,
                user = container.user,
                password = container.password,
                host = 'localhost',
                port = container.port
            )
            connection.close()
        except psycopg2.Error:
            print(f'Database not ready, retrying in {DB_RETRY_SECONDS} seconds...')
            time.sleep(DB_RETRY_SECONDS)
        else:
            print('Connectivity check successful.')
            out = True
    return out

def match_arg(args, arg_type):
    out = False

    for arg in args:
        if arg.strip() in ARGS[arg_type]:
            out = True
            break
    return out

def filter_args(args, filters):
    return [arg for arg in args if not any([match_arg([arg], filter) for filter in filters])]

def cd_back():
    path = get_key('BACKEND_PATH')

    if path == None:
        return False

    print('Changing to backend directory...')
    os.chdir(os.path.abspath(path))
    print(f'Current working directory: {os.getcwd()}')
    return True

def cd_front():
    path = get_key('FRONTEND_PATH')

    if path == None:
        return False

    print('Changing to frontend directory...')
    os.chdir(os.path.abspath(path))
    print(f'Current working directory: {os.getcwd()}')
    return True

def cd_key(key):
    if key == 'FRONTEND_PATH':
        return cd_front()
    elif key == 'BACKEND_PATH':
        return cd_back()
    else:
        return cd_proj()

def cd_proj():
    print('Changing to project directory...')
    os.chdir(CWD)
    print(f'Current working directory: {os.getcwd()}')

'''
COMMON COMMANDS
'''
def common_db(args, env):
    out = True

    if not cd_back():
        return False
    
    if env == 'dev':
        container_name = 'postgres'
    elif env == 'test':
        container_name = 'postgres-test'
    elif env == 'migr':
        container_name = 'postgres-devmigrations'

    containers = parse_docker_compose(Path(os.getcwd()))
    container = containers[container_name]

    if match_arg(args, 'RESET') or match_arg(args, 'STOP'):
        subprocess.run(['docker', 'compose', 'stop', container_name])
        subprocess.run(['docker', 'compose', 'down', '-v', container_name])

    if not match_arg(args, 'STOP'):
        subprocess.run(['docker', 'compose', 'up', '-d', container_name])
        out = check_db(container)
    cd_proj()
    return out

'''
BACK COMMANDS
'''
def back_db(args):
    return common_db(args, 'dev')

def back_seed(args):
    if not match_arg(args, 'NO_DB'):
        if not back_db(args):
            return False

    if not cd_back():
        return False
    
    subprocess.run([MVNW, 'spring-boot:run', '-Dspring-boot.run.profiles=seed'])
    cd_proj()
    return True

def back_run(args):
    if not match_arg(args, 'NO_DB'):
        if not back_seed(filter_args(args, ['STOP'])):
            return False

    if not cd_back():
        return False
    
    try:
        subprocess.run([MVNW, 'spring-boot:run', '-Dspring-boot.run.profiles=dev'])
    except KeyboardInterrupt:
        print("DondeSiempre backend terminated by user.")
    cd_proj()
    return True

def back_lint(args):
    if not cd_back():
        return False
    
    subprocess.run([MVNW, 'spotless:apply'])
    cd_proj()
    return True

def back_git(args):
    if not cd_back():
        return False
    
    subprocess.run(['git'] + args)
    cd_proj()
    return True

'''
FRONT COMMANDS
'''
def front_install(args):
    if not cd_front():
        return False
    
    subprocess.run([NPM, 'install'])
    cd_proj()
    return True

def front_run(args):
    if not cd_front():
        return False
    
    if match_arg(args, 'RESET'):
        subprocess.run(['docker', 'compose', 'stop', 'frontend'])
        subprocess.run(['docker', 'compose', 'down', '-v', 'frontend'])

    try:
        if match_arg(args, 'DOCKER'):
            subprocess.run(['docker', 'compose', 'up'])
        else:
            subprocess.run([NPM, 'run', 'dev'] + ['--no-cache' if match_arg(args, 'NO_CACHE') else ''])
    except KeyboardInterrupt:
        print("DondeSiempre frontend terminated by user.")
    cd_proj()
    return True

def front_lint(args):
    if not cd_front():
        return False
    
    subprocess.run([NPX, 'eslint', '--fix'])
    cd_proj()
    return True

def front_git(args):
    if not cd_front():
        return False
    
    subprocess.run(['git'] + args)
    cd_proj()
    return True

'''
TEST COMMANDS
'''
def test_db(args):
    return common_db(args, 'test')

def test_run(args):
    if not match_arg(args, 'NO_DB'):
        if not test_db(filter_args(args, ['STOP'])):
            return False

    if not cd_back():
        return False

    subprocess.run([MVNW, 'test'])
    cd_proj()
    return True

'''
MIGR COMMANDS
'''
def migr_db(args):
    return common_db(args, 'migr')

def migr_run(args):
    if not match_arg(args, 'NO_DB'):
        if not migr_db(filter_args(args, ['STOP'])):
            return False

    if not cd_back():
        return False
    
    subprocess.run([MVNW, 'liquibase:update'])

    if match_arg(args, 'GEN_MIGR'):
        subprocess.run([MVNW, 'clean', 'compile'])
        subprocess.run([MVNW, 'liquibase:diff'])
    cd_proj()
    return True

'''
ALL COMMANDS
'''
def lint_all(args):
    back_lint(args)
    front_lint(args)

'''
MAIN
'''
def execute_command(env, cmd, args):
    commands = {
        'back': {
            'db': back_db,
            'seed': back_seed,
            'run': back_run,
            'lint': back_lint,
            'git': back_git
        }, 'front': {
            'install': front_install,
            'run': front_run,
            'lint': front_lint,
            'git': front_git  
        }, 'test': {
            'db': test_db,
            'run': test_run,
        }, 'migr': {
            'db': migr_db,
            'run': migr_run,
        }, 'all': {
            'all': lint_all
        }
    }

    if env not in commands:
        print('Error: Invalid environment. Please supply a valid environment.')
    elif cmd not in commands[env]:
        print('Error: Invalid command. Please supply a valid command.')
    else:
        commands[env][cmd](args)

def usage():
    print('')
    print(2 * len(NAME) * '-')
    print(2 * len(NAME) * '-')
    print(NAME)
    print(2 * len(NAME) * '-')
    print('ISPP - Team DondeSiempre, 2026')
    print(2 *len(NAME) * '-')
    print('')
   
    print('This launcher script facilitates executing the DondeSiempre application.')
    print('')

    print(2 * len(NAME) * '-')
    print('Usage')
    print(2 * len(NAME) * '-')

    print('The launcher can be invoked in the following way:')
    print('\t- Windows: python -m launch <env>:<cmd> <args>')
    print('\t- Unix-like: python3 -m launch <env>:<cmd> <args>')
    print('')
   
    print('<env> must be one of the following environments:')
    print('\t- back: Backend development.')
    print('\t- front: Frontend development.')
    print('\t- test: Testing.')
    print('\t- migr: Migrations development.')
    print('\t- all: Frontend and backend development.')
    print('')
   
    print('<cmd> must be one of the following commands:')
   
    print('\t- For the "back" environment:')
    print('\t\t- db: Starts database container. Supported arguments:')
    print('\t\t\t-r, --reset: Resets the database container and volume.')
    print('\t\t\t-s, --stop: Stops the database container and volume.')
    print('')
    print('\t\t- seed: Seeds the database. Supported arguments:')
    print('\t\t\t-n, --nodb: Does not start the database container.')
    print('\t\t\t-r, --reset: Resets the database container and volume.')
    print('')
    print('\t\t- run: Executes the backend. Supported arguments:')
    print('\t\t\t-n, --nodb: Does not start the database container.')
    print('\t\t\t-r, --reset: Resets the database container and volume.')
    print('')
    print('\t\t- lint: Applies backend linter (Spotless).')
    print('\t\t- git: Executes any requested Git command in the backend repository.')
    print('')

    print('\t- For the "front" environment:')
    print('\t\t- install: Installs the frontend dependencies.')
    print('\t\t- run: Executes the frontend. Supported arguments:')
    print('\t\t\t-n, --nocache: Disables the cache.')
    print('\t\t\t-d, --docker: Executes the frotend using Docker.')
    print('')
    print('\t\t- lint: Applies frontend linter (ESLint).')
    print('\t\t- git: Executes any requested Git command in the frontend repository.')
    print('')

    print('\t- For the "test" environment:')
    print('\t\t- db: Starts database container. Supported arguments:')
    print('\t\t\t-r, --reset: Resets the database container and volume.')
    print('\t\t\t-s, --stop: Stops the database container and volume.')
    print('')
    print('\t\t- run: Executes jUnit tests. Supported arguments:')
    print('\t\t\t-n, --nodb: Does not start the database container.')
    print('\t\t\t-r, --reset: Resets the database container and volume.')
    print('')

    print('\t- For the "migr" environment:')
    print('\t\t- db: Starts database container. Supported arguments:')
    print('\t\t\t-r, --reset: Resets the database container and volume.')
    print('\t\t\t-s, --stop: Stops the database container and volume.')
    print('')
    print('\t\t- run: Applies existing migrations. Supported arguments:')
    print('\t\t\t-g, --gen: Generates new migrations.')
    print('\t\t\t-n, --nodb: Does not start the database container.')
    print('\t\t\t-r, --reset: Resets the database container and volume.')
    print('')

    print('\t- For the "all" environment:')
    print('\t\t- lint: Applies both the frontend and backend linters.')
    print('')
    
    print('Invoking the launcher using the "--help" argument will display this message and return.')
    print('')

    print(2 * len(NAME) * '-')
    print('Configuration')
    print(2 * len(NAME) * '-')

    print('The launcher must have a "launch.cfg" file placed alongside it.')
    print('If a command is invoked without said file, it will create an empty one and return.')
    print('')
    
    print('The "launch.cfg" file shall define the paths where the frontend and backend reside.')
    print('Its syntax is the following:')
    print('')

    print('\tBACKEND_PATH = /path/to/backend')
    print('\tFRONTEND_PATH = /path/to/frontend')
    print('')

    print('Please note the following:')
    print('\t- Paths can be either relative or absolute.')
    print('\t- Using "." notation is allowed.')
    print('\t- Paths must be unquoted.')
    print('\t- If a path is not set, the commands that require it will not do anything.')
    print('')

def main():
    if len(sys.argv) < 2 or '--help' in [arg.strip() for arg in sys.argv]:
        usage()
    else:
        args = [arg.strip() for arg in sys.argv[2:]]
        chunks = sys.argv[1].split(':')
        
        if len(chunks) < 2:
            print('Error: Please supply both an environment and command.')
            return
        
        env = chunks[0].strip()
        cmd = chunks[1].strip()
        
        execute_command(env, cmd, args)

if __name__ == '__main__':
    main()