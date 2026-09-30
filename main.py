import json
import random
import string

from pyscript import document, window

# ---------- data (single source of truth) ----------
AIRPORTS = {
    "NAIA": "Ninoy Aquino International Airport (NAIA)",
    "CRK": "Clark International Airport (CRK)",
}

ROUTES = {
    "CEB": {"name": "Cebu (CEB)",     "type": "DOM", "price": 5000,  "seats": 45},
    "ENI": {"name": "El Nido (ENI)",  "type": "DOM", "price": 6500,  "seats": 12},
    "NRT": {"name": "Tokyo (NRT)",    "type": "INT", "price": 15000, "seats": 88},
    "JFK": {"name": "New York (JFK)", "type": "INT", "price": 40000, "seats": 24},
    "DXB": {"name": "Dubai (DXB)",    "type": "INT", "price": 45000, "seats": 50},
}

CLASSES = {
    "ECO": {"label": "Economy", "surcharge": 0},
    "BUS": {"label": "Business", "surcharge": 50000},
}

# Multiplier on (route price + class surcharge). Multi-City 1.5 is a placeholder.
TRIPS = {"One-Way": 1, "Round-Trip": 2, "Multi-City": 1.5}


# ---------- helpers ----------
def el(element_id):
    return document.querySelector(f"#{element_id}")


def set_text(element_id, value):
    node = el(element_id)
    if node:
        node.textContent = value


def peso(amount):
    return f"₱{amount:,.2f}"


def load(key):
    raw = window.sessionStorage.getItem(key)
    return json.loads(raw) if raw else None


def save(key, data):
    window.sessionStorage.setItem(key, json.dumps(data))


def compute(booking, seat_fee_per_ticket=0):
    """Fare = (route price + class surcharge) x trip multiplier x tickets."""
    route = ROUTES[booking["route"]]
    surcharge = CLASSES[booking["travel_class"]]["surcharge"]
    tickets = booking["tickets"]
    fare = (route["price"] + surcharge) * TRIPS[booking["ticket_type"]] * tickets
    seat_fee = seat_fee_per_ticket * tickets
    return fare, seat_fee, fare + seat_fee


def make_sku(booking):
    # No seat count in the SKU, so it stays stable as seats sell.
    return f"SK-{ROUTES[booking['route']]['type']}-{booking['route']}-{booking['travel_class']}"


# ---------- index.html ----------
def update_routes(event=None):
    flight_type = el("flight_type").value
    route_el = el("route")

    if not flight_type:
        route_el.disabled = True
        route_el.innerHTML = '<option value="">Choose a flight type first</option>'
        return

    html = '<option value="">-- Select Route --</option>'
    for code, r in ROUTES.items():
        if r["type"] == flight_type:
            html += f'<option value="{code}">{r["name"]} - {peso(r["price"])}</option>'
    route_el.innerHTML = html
    route_el.disabled = False


def show_error(message):
    set_text("errorModalMessage", message)
    modal = window.bootstrap.Modal.getOrCreateInstance(el("errorModal"))
    modal.show()


def book_flight(event):
    first_name = el("first_name").value.strip()
    last_name = el("last_name").value.strip()
    airport = el("departure_airport").value
    flight_type = el("flight_type").value
    ticket_type = el("ticket_type").value
    route = el("route").value
    travel_class = el("travel_class").value
    tickets_raw = el("ticket_count").value

    if not first_name or not last_name or not airport or not flight_type \
            or not ticket_type or not route or not travel_class or not tickets_raw:
        show_error("Error: complete all fields before proceeding")
        return

    passenger = f"{first_name} {last_name}"

    tickets = int(float(tickets_raw))
    if tickets < 1:
        show_error("Error: you need at least 1 ticket")
        return

    seats = ROUTES[route]["seats"]
    if tickets > seats:
        show_error(f"Error: only {seats} seats are left on this route")
        return

    save("booking", {
        "passenger": passenger,
        "airport": airport,
        "ticket_type": ticket_type,
        "route": route,
        "travel_class": travel_class,
        "tickets": tickets,
    })
    window.sessionStorage.removeItem("sku")
    window.sessionStorage.removeItem("order")
    window.location.href = "sku.html"


# ---------- sku.html ----------
def seat_fee_now():
    seat_el = el("choose_seat")
    if not seat_el or seat_el.value == "":
        return None
    return float(seat_el.value)


def update_total(event=None):
    booking = load("booking")
    if not booking:
        return
    _, seat_total, total = compute(booking, seat_fee_now() or 0)
    set_text("s_seatfee", peso(seat_total))
    set_text("s_total", peso(total))


def show_receipt(order):
    set_text("r_ref", order["ref"])
    set_text("r_sku", order["sku"])
    set_text("r_passenger", order["passenger"])
    set_text("r_airport", AIRPORTS[order["airport"]])
    set_text("r_route", ROUTES[order["route"]]["name"])
    set_text("r_trip", order["ticket_type"])
    set_text("r_class", CLASSES[order["travel_class"]]["label"])
    set_text("r_tickets", str(order["tickets"]))
    set_text("r_seat", order["seat_choice"])
    set_text("r_fare", peso(order["fare"]))
    set_text("r_seatfee", peso(order["seat_fee"]))
    set_text("r_total", peso(order["total"]))

    el("form_card").classList.add("d-none")
    el("receipt_card").classList.remove("d-none")
    window.scrollTo(0, 0)


def init_sku():
    booking = load("booking")
    if not booking:
        window.alert("No booking found. Let's start from the beginning.")
        window.location.href = "index.html"
        return

    # Page refreshed after confirming: show the receipt again
    order = load("order")
    if order:
        show_receipt(order)
        return

    route = ROUTES[booking["route"]]
    fare, _, total = compute(booking, 0)
    set_text("s_passenger", booking["passenger"])
    set_text("s_airport", AIRPORTS[booking["airport"]])
    set_text("s_route", route["name"])
    set_text("s_trip", booking["ticket_type"])
    set_text("s_class", CLASSES[booking["travel_class"]]["label"])
    set_text("s_tickets", str(booking["tickets"]))
    set_text("s_seats", str(route["seats"]))
    set_text("s_fare", peso(fare))
    set_text("s_total", peso(total))


def generate_sku(event):
    booking = load("booking")
    if not booking:
        window.location.href = "index.html"
        return
    sku = make_sku(booking)
    window.sessionStorage.setItem("sku", sku)
    set_text("sku_output", f"Generated SKU: {sku}")


def purchase_additional(event):
    booking = load("booking")
    if not booking:
        window.location.href = "index.html"
        return

    fee = seat_fee_now()
    if fee is None:
        window.alert("Please choose a seat option before continuing!")
        return

    sku = window.sessionStorage.getItem("sku") or make_sku(booking)
    fare, seat_total, total = compute(booking, fee)
    ref = "AX-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

    order = {
        **booking,
        "sku": sku,
        "ref": ref,
        "seat_choice": "Chosen seat" if fee > 0 else "Random assignment",
        "fare": fare,
        "seat_fee": seat_total,
        "total": total,
    }
    save("order", order)
    show_receipt(order)


# ---------- run the right init for whichever page loaded this file ----------
if el("summary"):
    init_sku()
