#!/usr/bin/env python3

"""
inspect_ptyd_structure.py
-------------------------
Quickly list the top-level groups/datasets of a `.ptyd` file to sanity-check
that prepared data was written.

Usage:
  python inspect_ptyd_structure.py path/to/file.ptyd
"""
import sys
import h5py

def main():
    if len(sys.argv) != 2:
        print("Usage: python inspect_ptyd_structure.py <file.ptyd>")
        sys.exit(1)
    fn = sys.argv[1]
    with h5py.File(fn, "r") as f:
        def walk(name, obj):
            print(name, type(obj).__name__)
        f.visititems(walk)

if __name__ == "__main__":
    main()
