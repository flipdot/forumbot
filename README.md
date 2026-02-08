# flipdot Discourse bot

## Usage

    docker run -d -e DISCOURSE_API_KEY=fefe flipdot/forumbot
    # if you want to run on another discourse instance:
    docker run -d -e DISCOURSE_API_KEY=fefe -e DISCOURSE_USERNAME=hello -e DISCOURSE_HOST=https://forum.example.com flipdot/forumbot

## Deployment

Changes on the master branch are automatically build into a docker image and
published at [docker hub](https://hub.docker.com/r/flipdot/forumbot).
After it is published, you need to adjust [this ansible playbook](https://code.flipdot.org/flipdot-infra/ansible/src/branch/main/host_vars/spouting-whale.yml)

Checkout if a change to the ansible playbook is automatically deployed yet - at the time of writing this,
you need to run the playbook manually. See details over at the other repository.

## Developing

### Compose setup

If you are not able to get an API key for forum.flipdot.org, try the compose setup:

```
docker compose up
```

Go to http://localhost:3000/ and login with user `user@example.com` and password `bitnami123`

### Running

Clone this repo, make your changes, build a new container:

    ./build_docker.sh
    DISCOURSE_API_KEY=fefe ./run_docker.sh
    # or with the test user
    DISCOURSE_API_KEY=fefe DISCOURSE_USERNAME=flipbot_test ./run_docker.sh

Or, if you want to develop without docker:

    uv sync
    DISCOURSE_API_KEY=fefe uv run python src/app.py
    # or with the test user
    DISCOURSE_API_KEY=fefe DISCOURSE_USERNAME=flipbot_test uv run python src/app.py

You can get the credentials of flipdot_test in our forum: https://forum.flipdot.org/t/api-key-fuer-flipbot-test/3755

Copy .env.example to .env and set the API key there, so you don't have to set it every time.

    cp .env.example .env

Execute tests:

    PYTHONPATH=src uv run pytest

### How to add a job?

Start by copying `src/tasks/hello_world.py`. You can run your new task directly:

    uv run python src/app.py --dry --run_task hello_world

...where "hello_world" is the name of the python file.

Modify the `main()` function:

    def main(client: DiscourseClient) -> None:
        # Do your stuff here.
        # You can use the client object to interact with discourse
        pass

Next, open `src/app.py`. Add an `import tasks.my_awesome_task` to the top of the file.
Schedule your task inside the function `schedule_jobs`:

    schedule.every().day.at('13:37').do(tasks.my_awesome_task.main, client)

Take a look at [schedule](https://schedule.readthedocs.io/en/stable/) to see how to specify when to run your task.
