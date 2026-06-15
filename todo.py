tasks = []

while True:
    print("\n--- To Do List ---")
    print("1 Add Task")
    print("2 View Tasks")
    print("3 Delete Task")
    print("4 Exit ")

    choice  = input("Enter your choice: ")

    if choice == "1":
        task = input("Enter task: ")
        tasks.append(task)
        print("Task added")

    elif choice == "2":
        print("your task:")
        for i, task in enumerate(tasks):
            print(i + 1, ".", task)

    elif choice == "3":
        num = int(input("Enter tasks number: "))
        if 0 <= num <= len(tasks):
            tasks.pop(num - 1)
            print("Tasks deleted")
        else:
            print("Invalid number")

            
    elif choice == "4":
        print("bye")
        break
    else:
        print("Invalid choice")