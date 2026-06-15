#Define the menu of resturant
menu = {
    'Pizza': 60,
    'Burger': 50,
    'Coffee': 20,
    'Coca cola': 20,
    'Salad': 50,
}

#Greet
print("Welcome to PYTHON CAFE!")
print("Pizza: Rs60 \nBurger: Rs50 \nCoffee: Rs20 \nCoca cola: Rs20 \nSalad: Rs50")


order_total = 0
#60 + 50 = 110

item_1 = input("Enter the name of item you want to order= ")    
if item_1 in menu:
    order_total += menu[item_1] #0 + 50
    print(f"Your item {item_1} has been added to your order")

else:
    print(f"Ordered item {item_1} is not available in the menu!")

another_order = input("Do you want to add another item? (Yes/No) ")
if another_order == "Yes":
    item_2 = input("Enter the name of the second item: ")
    if item_2 in menu:
        order_total += menu[item_2]
        print(f"Your item {item_2} has been added to your order")
    else:
        print(f"Ordered item {item_2} is not available in the menu!")

print(f"The Total amount of items to pay is {order_total}")
