#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "ivo@marvan.cz"
__description__ = '''
English:https://en.wikipedia.org/wiki/Monty_Hall_problem

Veskrze poctivý moderátor umístil soutěžní cenu – auto – za jedny ze tří dveří. 
Za každými ze zbývajících dveří je cena útěchy – koza. 
Úkolem soutěžícího je zvolit si jedny dveře. 
Poté moderátor otevře jedny ze dvou zbývajících dveří, ale jen ty, za nimiž je koza. 
Teď má soutěžící možnost buď ponechat svou původní volbu, nebo změnit volbu na zbývající dveře. 

Co je pro soutěžícího výhodnější? Setrvat u své volby, nebo ji změnit?

Soutěžící vyhrává cenu, která je za dveřmi, které si zvolil. 
Soutěžící nemá žádné předchozí znalosti, které by mu umožnily odhalit, co je za dveřmi.

Viz https://cs.wikipedia.org/wiki/Monty_Hall%C5%AFv_probl%C3%A9m
Motivace: Luboš Pick - Jak napálit matfyzáka (MFF-FPF 14.12.2017), https://www.youtube.com/watch?v=tB_z17TBrNg 
'''

from random import choice

count_of_iter = 100000 # počet pokusů, které provedeme
debug = False # Chceme (při ladění) vypisovat jednotlivé experimenty?

doors_list = [1,2,3] # Máme troje dveře s čísly 1, 2 a 3
doors_set = set(doors_list) # pro výpočet použijem množinu dveří

number_of_succes_for_nochange = 0 # počet výher (auta) kdy při druhé volbě nedojde ke změně
number_of_succes_for_random_change = 0 # počet výher (auta) pro náhodnou změnu dveří při druhé volbě
number_of_succes_for_determ_change = 0 # počet výher (auta) deterministickou změnu dveří při druhé volbě

for i in range(0, count_of_iter):
    door_with_car = choice(doors_list) # auto je náhodně za dveřmi číslo 1, 2 nebo 3
    first_choice = choice(doors_list) # hráč nejprve náhodně vybere dveře číslo 1, 2 nebo 3

    # Moderátor (Monty Hall) otevře náhodně zbývající dveře s kozou.
    # Následující výpočet je v pořádku jak v případě, že v první volbě hráč dveře uhodl
    # (number_of_door_with_car == first_choice) a vybírá se náhodně ze dvou možností (dvě kozy na výběr),
    # tak v případě, že neuhodl a vybírá se z jedné možnosti (jedna koza na výběr).

    open_door_with_goat = choice(
        list(
            doors_set - {door_with_car} - {first_choice}
        )
    )

    if debug:
        print('#{}, car is in: {}, firt choice: {},  moderator open:{}'.format(
            i, door_with_car, first_choice, open_door_with_goat)
        )

    # Výpočet úspěšnosti pro tři strategie
    # 1. Hráč nemění svůj názor, setrvává u první volby.
    if door_with_car == first_choice:
        number_of_succes_for_nochange += 1

    # 2. Hráč mění svůj názor, a vybírá náhodně z neotevřených dveří.
    second_random_choice = choice(
        list(
            doors_set - {open_door_with_goat}
        )
    )
    if door_with_car == second_random_choice:
        number_of_succes_for_random_change += 1

    # 3. Hráč mění svůj názor, a vybírá si detrministicky dveře,
    # které nebyly vybrán při první volbě a nebyly otevřeny moderátorem.
    second_determ_choice = list(
            doors_set - {open_door_with_goat} - {first_choice}
        )[0]
    if door_with_car == second_determ_choice:
        number_of_succes_for_determ_change += 1
    
# výpis výsledků
print('Count of experiments: {}'.format(count_of_iter))
print('1. The player stays at the first choice.')
print('2. The player changes his choice and he chooses a door randomly again.')
print('3. The player changes his choice and he chooses deterministically unselected and unopened doors.')
print()
results = [number_of_succes_for_nochange, number_of_succes_for_random_change, number_of_succes_for_determ_change]
for i, result in enumerate(results):
    print('{}. The player wins {} times ({} %).'.format(i+1, result, 100 * result/count_of_iter))

