package main

import (
    "log"
    "net/http"
    "os"
)

func main() {
    dir, err := os.Getwd()
    if err != nil { log.Fatal(err) }
    fs := http.FileServer(http.Dir(dir))
    http.Handle("/", fs)
    log.Println("Server running at http://localhost:8080")
    err = http.ListenAndServe(":8080", nil)
    if err != nil { log.Fatal(err) }
}
