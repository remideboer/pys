# 2.11. A small contact book

Put the pieces together: variables, lists, functions, choices, and — if you
like — a file for persistence.

## Goal

A tiny program that:

1. Keeps a `list<string>` of contact names.
2. Can print all contacts.
3. Can add a name from keyboard input.
4. (Bonus) Saves the list to a text file and loads it on the next run
   (`Path.write_text` / `read_text`).

Sketch of the in-memory core:

```pys
import input from builtins

list<string> contacts = []

function void showContacts() {
    loop (string name in contacts) {
        print("- " + name)
    }
}

function void addContact(string name) {
    contacts.append(name)
}

string typed = input("New contact name: ")
addContact(typed)
showContacts()
```

*Interactive — type answers at the prompts; output depends on your input.*



> `list.append` adds one item (taught in [Data structures](basics_data.md)).
> If your tooling flags it, build a new list with
> `contacts = contacts + [typed]` instead.

Work in small steps. Get print-and-add working before you touch files.

### Exercise

> Finish the contact book to a point you can demo: add at least two names
> (hard-coded or via input) and print them. Optionally write each name on
> its own line in `contacts.txt`.

A fuller challenge lives under [Exercises](exercises_contact_book.md).

---

[Previous: Files](basics_files.md) · [Next: Spoilers](basics_spoilers.md)
