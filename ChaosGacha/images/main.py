from tkinter import *
import random
import os
def read_elements_and_weights(filename,avg,min,max):
    elements = []
    weights = []
    nweights = []
    minweight = float(min)
    midweight = float(avg)
    maxweight = float(max)
    if filename == 'all.txt':
        filename = ['abilities.txt','items.txt','familiars.txt','traits.txt', 'skills.txt']
        filename = [random.choice(filename)]
        for fname in filename:
            with open(fname, 'r') as file:
                for line in file:
                    parts = line.strip().split(',')
                    if len(parts) == 2:
                        element, weight = parts
                        if (float(weight) <= maxweight and minweight < float(weight)):
                            elements.append(element)
                            weights.append(1 / (pow(3, abs(midweight - (float(weight))))))  # Convert weight to integer
                            nweights.append(float(weight))

    else:
        with open(filename, 'r') as file:
            for line in file:
                parts = line.strip().split(',')
                if len(parts) == 2:
                    element, weight = parts
                    if(float(weight) <= maxweight and minweight < float(weight)):
                        elements.append(element)
                        weights.append(1/(pow(2.828,abs(midweight - (float(weight))))))  # Convert weight to integer
                        nweights.append(float(weight))
    return elements, weights, nweights

def run_gacha(v, avg, min, max):
    avg = float(randomizer(min,max,avg))
    round(avg,1)
    min = avg - 0.4
    max = avg + 0.4
    if(avg < 0.4):
        avg = 0.5
        min = 0.3
        max = 0.7
    if(v == 1):
        filename = 'abilities.txt'
    elif(v == 2):
        filename = 'items.txt'
    elif(v == 3):
        filename = 'familiars.txt'
    elif (v == 4):
        filename = 'traits.txt'
    elif (v == 5):
        filename = 'skills.txt'
    else:
        filename = 'all.txt'
    elements, weights, nweights = read_elements_and_weights(filename,avg,min,max)

    # Perform 10 weighted random choices
    selected_indices = random.choices(range(len(elements)), weights=weights, k=1)
    totalweight = sum(weights)
    pulledtotal = 0
    # Print each selected element and its weight
    for index in selected_indices:
        selected_element = elements[index]
        selected_weight = nweights[index]
        selected_rweight = weights[index]
        print(
            f"Selected element: {selected_element} with weight: {selected_weight} and {round(100 * selected_rweight / totalweight, 2)}% odds")
        result = f"{selected_element} {selected_weight} - {round(100 * selected_rweight / totalweight, 2)}%"
        label.config(text=result)
        if selected_weight < 1.0:
            label.config(fg='#321')
        elif selected_weight < 2.0:
            label.config(fg='#A74')
        elif selected_weight < 3.0:
            label.config(fg='#DDF')
        elif selected_weight < 4.0:
            label.config(fg='#3D3')
        elif selected_weight < 5.0:
            label.config(fg='#37F')
        elif selected_weight < 6.0:
            label.config(fg='#707')
        elif selected_weight < 7.0:
            label.config(fg='#F6F')
        elif selected_weight < 8.0:
            label.config(fg='#F60')
        elif selected_weight < 9.0:
            label.config(fg='#FC0')
        else:
            label.config(fg='#F00')
        pulledtotal += selected_weight

def button_click():
    global v
    global w
    global min
    global max
    # Define the variable you want to pass to the command
    d = v.get()
    run_gacha(d,w.get(),min.get(),max.get())

def button_click2():
    global v
    d = v.get()
    update_gacha(d)

def randomizer(min,max,avg):
    floatmax = float(max)
    floatmin = float(min)
    floatavg = float(avg)
    x = floatmin
    randarr = []
    weights = []
    while(x < floatmax):
        randarr.append(x)
        x+=0.01
        weights.append(1 / (pow(5.0, abs(floatavg - (float(x))))))  # Convert weight to integer
    realweight = random.choices(randarr, weights, k=1)
    #print(realweight)
    return float(realweight[0])


def update_gacha(v):
    if (v == 1):
        filename = 'abilities.txt'
    elif (v == 2):
        filename = 'items.txt'
    elif (v == 3):
        filename = 'familiars.txt'
    elif (v == 4):
        filename = 'traits.txt'
    elif (v == 5):
        filename = 'skills.txt'
    else:
        filename = 'all.txt'
    os.startfile(filename)

def button_click3():
    # w min max
    if w.get() == '1.3':
        w.delete(0, "end")
        w.insert(0, 2.3)
        min.delete(0, "end")
        min.insert(0, 0.0)
        max.delete(0, "end")
        max.insert(0, 5.3)
    elif w.get() == '2.3':
        w.delete(0, "end")
        w.insert(0, 3.3)
        min.delete(0, "end")
        min.insert(0, 0.0)
        max.delete(0, "end")
        max.insert(0, 6.3)
    elif w.get() == '3.3':
        w.delete(0, "end")
        w.insert(0, 4.3)
        min.delete(0, "end")
        min.insert(0, 1.0)
        max.delete(0, "end")
        max.insert(0, 7.3)
    elif w.get() == '4.3':
        w.delete(0, "end")
        w.insert(0, 5.3)
        min.delete(0, "end")
        min.insert(0, 2.5)
        max.delete(0, "end")
        max.insert(0, 9.3)
    else:
        w.delete(0, "end")
        w.insert(0, 1.3)
        min.delete(0, "end")
        min.insert(0, 0.0)
        max.delete(0, "end")
        max.insert(0, 4.3)


global v
global w
global min
global max
global gachaname
global gachaweight
root = Tk()
root.title('Gacha Puller')
root.configure(background='#111')
v = IntVar()
label = Label(root, text="Result will appear here", pady=30, bg='#111', font=("Arial", 22))
label.pack()
button = Button(root, text='Run', width=25, command=button_click, background='#111', fg='#FFF')
button.pack()
button2 = Button(root, text='Edit', width=25, command=button_click2, background='#111', fg='#FFF')
button2.pack()
Radiobutton(root, text='Ability', variable=v, value=1, background='#111', fg='#FFF',selectcolor='black').pack(anchor=W)
we = Button(root, text='Preset', width=8, command=button_click3, background='#111', fg='#FFF')
we.pack(side=RIGHT)
Radiobutton(root, text='Item', variable=v, value=2, background='#111', fg='#FFF',selectcolor='black').pack(anchor=W)
Radiobutton(root, text='Familiar', variable=v, value=3, background='#111', fg='#FFF',selectcolor='black').pack(anchor=W)
Radiobutton(root, text='Traits', variable=v, value=4, background='#111', fg='#FFF',selectcolor='black').pack(anchor=W)
Radiobutton(root, text='Skills', variable=v, value=5, background='#111', fg='#FFF',selectcolor='black').pack(anchor=W)
Radiobutton(root, text='All', variable=v, value=6, background='#111', fg='#FFF',selectcolor='black').pack(anchor=W)
w = Spinbox(root, from_=0.0, to=10.0, format="%.1f",increment=0.1, width=4, relief="sunken", repeatdelay=500, repeatinterval=100,font=("Arial", 12), bg="#111", fg="#FFF")
min = Spinbox(root, from_=0.0, to=10.0, format="%.1f",increment=0.1, width=4, relief="sunken", repeatdelay=500, repeatinterval=100,font=("Arial", 12), bg="#111", fg="#FFF")
max = Spinbox(root, from_=0.0, to=10.0, format="%.1f",increment=0.1, width=4, relief="sunken", repeatdelay=500, repeatinterval=100,font=("Arial", 12), bg="#111", fg="#FFF")
label1 = Label(root, text="Average: ", background='#111', fg='#FFF')
label1.pack(side=LEFT)
w.pack(side=LEFT)
label2 = Label(root, text="Minimum: ", background='#111', fg='#FFF')
label2.pack(side=LEFT,padx=5)
min.pack(side=LEFT)
label3 = Label(root, text="Maximum: ", background='#111', fg='#FFF')
label3.pack(side=LEFT, padx=5)
max.pack(side=LEFT)
w.delete(0,"end")
w.insert(0,1.3)
min.delete(0,"end")
min.insert(0,0.0)
max.delete(0,"end")
max.insert(0,4.3)
mainloop()