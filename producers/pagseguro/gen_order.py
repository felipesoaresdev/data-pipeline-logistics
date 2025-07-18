import uuid
import json
from random import randint, choice
import pendulum
from faker import Faker

# sys.path.append(os.getcwd())
from producers.pagseguro.dataset.produtos_tech import produtos

fake = Faker("pt_BR")
Faker.seed(0)


def gen_credit_card():
    first_digits = {
        "visa": [
            ["4", "5", "3", "9"],
            ["4", "5", "5", "6"],
            ["4", "9", "1", "6"],
            ["4", "5", "3", "2"],
            ["4", "9", "2", "9"],
            ["4", "4", "8", "6"],
            ["4", "7", "1", "6"],
        ],
        "master": [
            ["5", "1"] + [str(randint(0, 0)) for _ in range(2)],
            ["5", "2"] + [str(randint(0, 10)) for _ in range(2)],
            ["5", "3"] + [str(randint(0, 10)) for _ in range(2)],
            ["5", "4"] + [str(randint(0, 10)) for _ in range(2)],
            ["5", "5"] + [str(randint(0, 10)) for _ in range(2)],
        ],
    }
    brand = choice(["visa", "master"])
    return {
        "brand": brand,
        "first_digits": "".join(choice(first_digits[brand])),
        "last_digits": "".join([str(randint(0, 10)) for _ in range(4)]),
    }


def gen_payment_method(customer):
    name = customer["name"]
    credit_card = gen_credit_card()
    payment_methods = {
        "PIX": {
            "type": "PIX",
            "pix": {
                "notification_id": "NTF_" + str(uuid.uuid4()),
                "end_to_end_id": str(uuid.uuid4()).replace("-", ""),
                "holder": {
                    "name": name,
                    "tax_id": ("***" + customer["tax_id"][4:-3] + "**").replace(
                        ".", ""
                    ),
                },
            },
        },
        "CREDIT_CARD": {
            "type": "CREDIT_CARD",
            "card": {
                "brand": credit_card["brand"],
                "first_digits": credit_card["first_digits"],
                "last_digits": credit_card["last_digits"],
                "exp_month": randint(1, 12),
                "exp_year": randint(2025, 2032),
                "holder": {"name": name},
            },
        },
    }

    if randint(0, 10) > 4:
        return payment_methods["CREDIT_CARD"]
    return payment_methods["PIX"]


def get_randon_customer(customers_file=None):
    if customers_file is None:
        customers_file = "producers/pagseguro/dataset/customers_llm.json"
    with open(customers_file, "r", encoding="utf-8") as f:
        data = f.read()
        customers = json.loads(data)

        the_chosen_one = choice(customers)
        # print(the_chosen_one)
        return the_chosen_one


def get_random_product():
    the_chosen_one = choice(produtos)
    the_chosen_one["quantity"] = 1
    return the_chosen_one


def gen_charge(customer, products, created_at):
    paid_at = created_at.add(minutes=randint(0, 15), seconds=randint(5, 60))

    total_value = 0
    for item in products:
        total_value += item["quantity"] * item["unit_price"]

    charges = [
        {
            "id": "CHAR_" + str(uuid.uuid4()),
            "reference_id": "referencia da cobranca",
            "status": "PAID",
            "created_at": str(created_at),
            "paid_at": str(paid_at),
            "description": "descricao da cobranca",
            "amount": {
                "value": total_value,
                "currency": "BRL",
                "summary": {"total": total_value, "paid": total_value, "refunded": 0},
            },
            "payment_method": gen_payment_method(customer),
        }
    ]
    return charges


class OrderGen:
    def __init__(self) -> None:
        pass

    def generate(self, dt=None, customers_file=None, products_file=None):
        customer = get_randon_customer(customers_file=customers_file)

        if dt is None:
            fake_dt = fake.date_between(
                start_date=pendulum.from_format(
                    customer["created_at"], "YYYY-MM-DD", tz="America/Fortaleza"
                ),
                end_date="-1d",
            )

            created_at = pendulum.from_format(
                str(fake_dt), "YYYY-MM-DD", tz="America/Fortaleza"
            ).add(hours=randint(0, 23), minutes=randint(0, 60), seconds=randint(0, 60))
        else:
            created_at = pendulum.now("America/Fortaleza")

        address = customer["address"]
        del customer["address"]

        items = [get_random_product() for _ in range(1, randint(2, 5))]

        order = {
            "id": "ORDE_" + str(uuid.uuid4()),
            "reference_id": "re_" + str(uuid.uuid4()),
            "created_at": str(created_at),
            "shipping": address,
            "items": items,
            "customer": customer,
            "charges": gen_charge(customer, items, created_at),
        }

        return order


if __name__ == "__main__":
    import json
    import os

    order_gen = OrderGen()

    total = 10
    chunk = 1000

    orders = []
    first = 0

    folder = "producers/pagseguro/dataset/orders/"
    os.makedirs(folder, exist_ok=True)
    for n in range(1, total + 1):
        orders.append(order_gen.generate())
        if n % chunk == 0:
            print(f"{first}-{n}.json")

            with open(f"{folder}/{first}-{n}.json", "w", encoding="utf-8") as f:
                f.write(json.dumps(orders, indent=4))
            orders = []
            first = n + 1
    if len(orders) > 0:
        with open(f"{folder}/{first}-{n}.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(orders, indent=4))
