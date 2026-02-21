# Met een functie
def create_dog(name, age):
    return {"name": name, "age": age}

def bark(dog):
    return f"{dog['name']} zegt woef!"

my_dog = create_dog("Buddy", 3)
print(my_dog["name"])  # Output: Buddy
print(bark(my_dog))  # Output: Buddy zegt woef!

# Met een class
class Dog:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def bark(self):
        return f"{self.name} zegt woef!"

my_dog = Dog("Buddy", 3)
print(my_dog.name)  # Output: Buddy
print(my_dog.bark())  # Output: Buddy zegt woef!
