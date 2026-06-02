from rich.progress import Progress
from time import sleep

with Progress() as pb:
    nodetask = pb.add_task("Procesing nodes...", total=14)
    proptask = pb.add_task("Processing properties...", total=25)

    for i in range(14):
        for j in range(25):
            print(f"i:j\t{i}:{j}")
            sleep(0.2)
            pb.update(task_id=proptask, completed=j+1)
        pb.update(task_id=nodetask, completed=i+1)

