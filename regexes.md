# Regex collection

## IMDB regexes

### New imdb movie table

```[regex]
^(?:("{0,1}[0-9]{1,3}))\.
$1,

\((?:([0-9]{4}\)))
,$1

(?:([0-9]{4}))\)
$1
```

### Old imdb movie table

```[regex]
(?:("(.*)))\((?:([0-9]{4}\)))
$1",$3

(?:([0-9]{4}))\)"
$1
```

## classreal

```[regex]
<br>
\n

</p><p><a name="[A-Z]"></a><b>[A-Z]</b>\n
none

\[.*
none

\((?:([0-9]{4}\)))
,$1

(.*)(?:( ,))
"$1",
```

## wikipedia academy top foreign films

### nominees and winners

```[regex]
(<table class="wikitable".*>)((.|\n)+?)(</table>)
Ctrl+Shift+L, Ctrl+X, Ctrl+V

"([0-9]{4})(\n)(\([0-9]{2}[a-z]{2}\)")
$1

(,)(".*)(\n)(.*")
$1$2 $4

<span data-sort-value="".+?"">
none

^(?!([0-9]{4}))
,$1
```

### shortlist

```[regex]
,\[[0-9]{1,2}\]
none

 \( .+?\), 
"\n,"

 \( .+?\)
none
```
