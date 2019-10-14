# flipdot Discourse bot

## Usage

    docker run -d -e DISCOURSE_API_KEY=fefe flipdot/forumbot

## Deployment

The python script is running on a pi (without docker). When the pi boots, it
will pull this repo, execute `pip install -r requirements.txt` and starts
`app.py`. You just need to repower the correct pi in the space ;)

## Developing

### Running

Clone this repo, make your changes, build a new container:

    ./build_docker.sh
    DISCOURSE_API_KEY=fefe ./run_docker.sh

Or, if you want to develop without docker:

    pip install -r requirements.txt
    DISCOURSE_API_KEY=fefe python src/app.py
    
Execute tests:

    pip install nose
    nosetests tests

### How to add a job?

1. Open `src/tasks.py`. Add a new function

        def my_awesome_task(client: DiscourseClient):
            # Do your stuff here.
            # You can use the client object to interact with discourse
            pass

2. Open `src/app.py`. Schedule your task inside function `schedule_jobs`:

        schedule.every().day.at('13:37').do(tasks.my_awesome_task, client)

   Take a look at [schedule](https://schedule.readthedocs.io/en/stable/) to see how to specify when to run your task.
