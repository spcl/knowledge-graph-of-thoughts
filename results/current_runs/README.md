# Compression / Decompression instructions

There are multiple ways to compress and decompress the data. The following instructions will help you to do that.
This guide will help yuo with two of the best methods to compress and decompress the data `xz` and `zstd`.

- [Compression / Decompression instructions](#compression--decompression-instructions)
  - [Using `xz` command line tool](#using-xz-command-line-tool)
    - [Compressing](#compressing)
    - [Decompressing](#decompressing)
  - [Using `zstd` command line tool](#using-zstd-command-line-tool)
    - [Compressing](#compressing-1)
    - [Decompressing](#decompressing-1)

## Using `xz` command line tool

Pros:

- Very good compression ratio.
- Fast decompression.
- Good for large files.
  
Cons:

- Slow compression.
- Single-threaded.

### Compressing

Compression level ranges from 0 to 9, where 0 is no compression and 9 is maximum compression.

- Any compression level more than 3 is good for this dataset.
- We want to stay under 500MB total. Thus adjust the compression level accordingly.
- Level 9 takes approsimately 3 minutes on a M4 CPU.
- Level 4 takes approximately 50 seconds minute on a M4 CPU.

```bash
tar -cJf - --options='xz:compression-level=4' */ | split -b 50M - archive.tar.xz.part_
```

### Decompressing

Use the following command when the files contains a `.tar.xz` part.

```bash
cat archive.tar.xz.part_* | tar -xJf -
```

If the files are not split, use the following command.

```bash
tar -xJf archive.tar.xz
```

## Using `zstd` command line tool

Pros:

- Good compression ratio.
- Fast compression and decompression.
- Multi-threaded.
Cons:
- Not as good as `xz` for large files.
- Not as widely used as `xz`.

### Compressing

Compression level ranges from 1 to 22, where 1 is no compression and 22 is maximum compression.

- Any compression level more than 6 is good for this dataset.
- We want to stay under 500MB total. Thus adjust the compression level accordingly.
- Level 19 takes approsimately 30 seconds on 14 core M4 CPU.
- Level 6 takes approximately 5 seconds on 14 core M4 CPU.

```bash
tar -cf - */ | zstd -6 -T14 | split -b 50M - archive.tar.zst.part_  
```

### Decompressing

Use the following command when the files contains a `.tar.zst` part.

```bash
cat archive.tar.zst.part_* | zstd -d | tar -xf -
```

If the files are not split, use the following command.

```bash
zstd -d archive.tar.zst | tar -xf -
```
