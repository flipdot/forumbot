from datetime import datetime, date

import matplotlib.pyplot as plt
import pandas as pd
import pytz
import yaml


def plot_gantt_chart(
    voucher, start_date: date, end_date: date, exhausted_at: datetime | None = None
):
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date) + pd.Timedelta(days=1)
    data = []
    last_end = start_date
    for i, voucher_entry in enumerate(voucher):
        history = voucher_entry["history"]
        for j, entry in enumerate(
            sorted(history, key=lambda x: datetime.fromisoformat(x["received_at"]))
        ):
            start = pd.to_datetime(entry["received_at"])
            if "returned_at" in entry:
                end = pd.to_datetime(entry["returned_at"])
            elif j + 1 < len(history):
                end = pd.to_datetime(history[j + 1]["received_at"])
            else:
                end = min(
                    pd.to_datetime("now", utc=True).tz_convert("Europe/Berlin"),
                    end_date,
                )

            if entry["persons"] > 1:
                extra_persons = f" + {entry['persons'] - 1}"
            else:
                extra_persons = ""
            data.append(
                {
                    "voucher_id": f"#{i + 1}",
                    "username": entry["username"],
                    "text": f"{entry['username']}{extra_persons}",
                    "start": start,
                    "end": end,
                }
            )
            last_end = end
        if end_date > datetime.now().astimezone(pytz.timezone("Europe/Berlin")):
            days_left = (end_date - last_end).days

            if days_left <= 0:
                text = ""
            elif days_left == 1:
                text = "noch max\n1 Tag"
            else:
                text = f"noch max\n{days_left} Tage"
            data.append(
                {
                    "voucher_id": f"#{i + 1}",
                    "username": "",
                    "text": text,
                    "start": last_end,
                    "end": end_date,
                }
            )

    if not data:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.set_title("Voucherstats")
        ax.text(
            0.5,
            0.5,
            "Noch keine historischen Daten verfügbar",
            va="center",
            ha="center",
            fontsize=16,
        )
        return fig

    # Convert data to DataFrame and process dates
    df = pd.DataFrame(data)
    # df["start"] = pd.to_datetime(df["start"])
    # df["end"] = pd.to_datetime(df["end"])
    df["duration"] = df["end"] - df["start"]

    # Unique colors for each user
    # Drop the "empty string" username so it doesn't affect the color mapping
    usernames = df["username"].unique()
    usernames = usernames[usernames != ""]
    user_colors = {user: plt.cm.tab20(i) for i, user in enumerate(usernames)}

    fig, ax = plt.subplots(figsize=(12, 6))

    # Loop over each voucher and each record within each voucher
    voucher_ids = df["voucher_id"].unique()[::-1]
    for voucher_id in voucher_ids:
        voucher_data = df[df["voucher_id"] == voucher_id]
        for _, row in voucher_data.iterrows():
            start = row["start"]
            duration = row["duration"]
            if row["username"] == "":
                kwargs = {
                    "color": "white",
                    "edgecolor": "#aaaaaa",
                    "hatch": "////",
                }
            else:
                kwargs = {
                    "color": user_colors[row["username"]],
                    "edgecolor": "black",
                }

            ax.barh(
                voucher_id,
                duration,
                left=start.to_pydatetime(),
                **kwargs,
            )
            ax.text(
                start.to_pydatetime() + duration / 2,
                voucher_id,
                row["text"],
                va="center",
                ha="center",
                color="black",
                fontsize=8,
                weight="bold",
            )

    if exhausted_at:
        ax.axvline(
            exhausted_at, color="red", linestyle="--", label="Kontingent erschöpft"
        )
        ax.text(
            exhausted_at,
            len(voucher_ids) - 0.5,
            "Kontingent erschöpft",
            va="bottom",
            ha="center",
            color="red",
            fontsize=12,
            weight="bold",
            backgroundcolor="white",
        )

    ax.set_title("Voucherstats")
    ax.set_yticks(range(len(voucher_ids)))
    ax.set_yticklabels(voucher_ids)

    start_date = pd.to_datetime(start_date)
    date_range = pd.date_range(start_date.tz_convert("UTC"), end_date.tz_convert("UTC"))
    date_range = date_range.tz_convert("Europe/Berlin")

    ax.set_xticks(date_range)
    ax.set_xticklabels(date_range.strftime("%Y-%m-%d"), rotation=90)

    plt.tight_layout()
    return fig


if __name__ == "__main__":
    with open("new_storage.yaml") as f:
        store = yaml.safe_load(f.read())

    fig = plot_gantt_chart(
        store["voucher"],
        start_date=date(2024, 10, 22),
        end_date=date(2024, 11, 11),
        exhausted_at=datetime(2024, 11, 5, 12, 26),
    )
    fig.show()
