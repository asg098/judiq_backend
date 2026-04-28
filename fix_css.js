const fs = require('fs');
const path = require('path');

const filePath = path.join(__dirname, '..', 'styles.css');
let content = fs.readFileSync(filePath);

// Look for the mangled pattern
const mangledIndex = content.indexOf(Buffer.from('@\x00 k\x00 e\x00 y\x00 f\x00 r\x00 a\x00 m\x00 e\x00 s\x00'));
if (mangledIndex !== -1) {
    fs.writeFileSync(filePath, content.slice(0, mangledIndex));
    console.log('Fixed UTF-16 mangled line');
} else {
    const mangledIndex2 = content.indexOf('@ k e y f r a m e s');
    if (mangledIndex2 !== -1 && mangledIndex2 > content.length - 200) {
        fs.writeFileSync(filePath, content.slice(0, mangledIndex2));
        console.log('Fixed spaced mangled line');
    } else {
        console.log('Mangled line not found');
    }
}
