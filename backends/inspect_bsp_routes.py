import inspect
import app.main


def walk(routes, prefix=""):
    for route in routes:

        # Nested FastAPI router
        if hasattr(route, "routes"):
            nested_prefix = prefix + getattr(
                route,
                "prefix",
                "",
            )

            walk(
                route.routes,
                nested_prefix,
            )

            continue

        path = getattr(
            route,
            "path",
            "",
        )

        full_path = prefix + path

        if full_path.startswith("/bsp"):

            print()
            print("=" * 80)
            print("PATH:", full_path)
            print("=" * 80)

            print(
                "METHODS:",
                getattr(
                    route,
                    "methods",
                    None,
                ),
            )

            endpoint = getattr(
                route,
                "endpoint",
                None,
            )

            print(
                "ENDPOINT:",
                endpoint,
            )

            if endpoint:

                try:
                    print()
                    print(
                        inspect.getsource(
                            endpoint
                        )
                    )

                except Exception as exc:
                    print(
                        "Could not read source:",
                        exc,
                    )


walk(
    app.main.app.routes
)