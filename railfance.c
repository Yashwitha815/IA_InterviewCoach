#include <stdio.h>
#include <string.h>

void encrypt(char text[], int rails, char cipher[])
{
    int len, row, direction, i, k;

    len = strlen(text);
    row = 0;
    direction = 1;
    k = 0;

    for (i = 0; i < rails; i++)
    {
        row = i;

        while (row < len)
        {
            cipher[k++] = text[row];

            if (i == 0 || i == rails - 1)
                row += 2 * (rails - 1);
            else
            {
                row += 2 * (rails - 1 - i);

                if (row < len)
                    cipher[k++] = text[row];

                row += 2 * i;
            }
        }
    }

    cipher[k] = '\0';
}

void decrypt(char cipher[], int rails, char plain[])
{
    int len, i, j, row, direction, index;
    int mark[100];

    len = strlen(cipher);

    for (i = 0; i < len; i++)
        mark[i] = 0;

    row = 0;
    direction = 1;

    for (i = 0; i < len; i++)
    {
        mark[i] = row;

        if (row == 0)
            direction = 1;
        else if (row == rails - 1)
            direction = -1;

        row += direction;
    }

    index = 0;

    for (j = 0; j < rails; j++)
    {
        for (i = 0; i < len; i++)
        {
            if (mark[i] == j)
            {
                plain[i] = cipher[index++];
            }
        }
    }

    plain[len] = '\0';
}

int main()
{
    char text[100];
    char cipher[100];
    char plain[100];
    int rails;

    printf("Enter text: ");
    fgets(text, 100, stdin);

    text[strcspn(text, "\n")] = '\0';

    printf("Enter number of rails: ");
    scanf("%d", &rails);

    if (rails < 2)
    {
        printf("Number of rails must be at least 2.\n");
        return 1;
    }

    encrypt(text, rails, cipher);
    decrypt(cipher, rails, plain);

    printf("Encrypted text: %s\n", cipher);
    printf("Decrypted text: %s\n", plain);

    return 0;
}