# read tmp.output file

filename=$1
specname=$2

# Remove all rows between <<< generate and <<< solve from filename and copy them in a separate file
sed -n -e '/<<< generate/,/<<< solve/p' "$filename" > "$specname"
sed -i -e '/<<< generate/,/<<< solve/d' "$filename"

# Remove all rows starting with <<<
sed -i -e '/^<<<\s/d' "$filename"
sed -i -e '/^<<<\s/d' "$specname"

# Remove spaces before [ and at the start of the line
sed -i 's/\s*\[/[/g' "$filename"
sed -i 's/^\s*//g' "$filename"


while grep -q '^[0-9]' "$filename"; do
    sed -i -E '/\[/{N;s/\n/ /;s/(, )+/,\n/g}' "$filename"
    sed -i -E '/^[a-z]/s/^/\n/' "$filename"
done

# replace [ [ with [\n[
sed -i -E 's/\[ \[/\[\n\[/g' "$filename"

# Replace spaces between two numbers separated by just a space with a comma
sed -i -E 's/([0-9]) ([0-9])/\1,\2/g' "$filename"
sed -i -E 's/([0-9]) ([0-9])/\1,\2/g' "$filename"

# replace ] <spaces> <letter> with ]\n<letter>
sed -i -E 's/\] ([a-zA-Z])/\]\n\1/g' "$filename"

# Convert OBJECTIVE line to objective assignment
sed -i -E 's/OBJECTIVE: (.*)/objective = \1/g' "$filename"

# save
cp $filename $3